"""Phase 1 smoke test: N sequential Basic-env rollouts, one fresh Surfnet each.

    uv run python scripts/smoke_rollouts.py --dry-run            # no LLM, proves env boots
    OPENROUTER_API_KEY=... uv run python scripts/smoke_rollouts.py --n 2 --max-messages 10

Writes one JSON line per rollout to --out. Never writes the API key anywhere.
"""
import argparse
import asyncio
import base64
import json
import logging
import os
import socket
import sys
import time
from pathlib import Path

import requests
from solders.transaction import Transaction

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.chdir(Path(__file__).resolve().parent.parent)

from code_loop_explorer import CodeLoopExplorer  # noqa: E402
from voyager.skill_manager.ts_skill_manager import TypeScriptSkillManager  # noqa: E402
from voyager.surfpool_env import SurfpoolEnv, _surfpool_validator  # noqa: E402

FORK_RPC = "https://api.mainnet-beta.solana.com"  # free public RPC, read-only lazy fork
CODE_FILE = "voyager/environments/basic_runtime/code_loop_code.ts"
MEMO_PROGRAMS = {
    "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",  # Memo v2
    "Memo1UhkJRfHyvLMcVucJwxXeuD8nmfcKE4pYoQRB2c",  # Memo v1
}

DRY_RUN_SKILL = """
import { Transaction, TransactionInstruction, PublicKey } from "@solana/web3.js";
export async function executeSkill(blockhash: string): Promise<string> {
  const agent = new PublicKey(process.argv[4]);
  const tx = new Transaction({ feePayer: agent, recentBlockhash: blockhash });
  tx.add(new TransactionInstruction({
    programId: new PublicKey("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"),
    keys: [], data: Buffer.from("dry-run"),
  }));
  return tx.serialize({ requireAllSignatures: false, verifySignatures: false }).toString("base64");
}
"""


def key_usage() -> float | None:
    """Total USD spent on this OpenRouter key so far (free endpoint, no credits used)."""
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return None
    r = requests.get("https://openrouter.ai/api/v1/key",
                     headers={"Authorization": f"Bearer {key}"}, timeout=20)
    r.raise_for_status()
    return r.json()["data"].get("usage")


def port_busy(port: int = 8899) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def score_breakdown(env: SurfpoolEnv) -> dict:
    by_prog: dict[str, int] = {}
    for prog, _disc in env.program_instructions_seen:
        by_prog[str(prog)] = by_prog.get(str(prog), 0) + 1
    memo = sum(v for k, v in by_prog.items() if k in MEMO_PROGRAMS)
    return {"points_by_program": by_prog, "memo_points": memo,
            "non_memo_points": sum(by_prog.values()) - memo}


async def one_rollout(i: int, args) -> dict:
    if port_busy():
        raise RuntimeError("port 8899 already in use; refusing to share a validator")
    t0 = time.time()
    async with _surfpool_validator(FORK_RPC):
        env = SurfpoolEnv(use_external_surfpool=True)  # throwaway random keypair, 2 SOL airdrop
        await env.reset()
        rec = {"rollout": i, "model": None if args.dry_run else args.model,
               "env": "basic", "max_messages": args.max_messages,
               "max_output_tokens": None if args.dry_run else (args.max_output_tokens or None),
               "provider_order": args.provider,
               "agent_pubkey": str(env.agent_keypair.pubkey())}
        try:
            if args.dry_run:
                sm = TypeScriptSkillManager(model_name="none", ckpt_dir="ckpt/smoke")
                Path(CODE_FILE).write_text(DRY_RUN_SKILL)
                bh = str((await env.client.get_latest_blockhash()).value.blockhash)
                res = sm.run_code_loop_code(DRY_RUN_SKILL, rec["agent_pubkey"], bh, CODE_FILE, 4000)
                tx = Transaction.from_bytes(base64.b64decode(res["serialized_tx"]))
                signed = env._partial_sign_transaction(bytes(tx), [env.agent_keypair])
                _, reward, *_ = await env.step(signed)
                rec.update(messages=0, dry_run_reward=reward)
            else:
                ex = CodeLoopExplorer(model_name=args.model, run_index=i,
                                      max_messages=args.max_messages, verbose=False,
                                      code_file=CODE_FILE, environment_config="basic",
                                      max_output_tokens=args.max_output_tokens or None,
                                      provider_order=args.provider or None)
                await ex.run_exploration_loop(env)
                ex.save_checkpoint()
                m = ex.metrics
                usage = m["llm_usage"]
                turns = m["messages"]
                rec.update(
                    run_id=ex.run_id, messages=ex.message_count,
                    per_turn_reward=[t["reward"] for t in turns],
                    code_blocks=len(m["code_blocks_extracted"]),
                    successful_txs=sum(1 for c in m["code_blocks_extracted"] if c["success"]),
                    errors=len(m["errors"]),
                    prompt_tokens=sum(u["prompt_tokens"] or 0 for u in usage),
                    completion_tokens=sum(u["completion_tokens"] or 0 for u in usage),
                    reasoning_tokens=sum(u["reasoning_tokens"] or 0 for u in usage),
                    cost_usd_reported=round(sum(u["cost"] or 0 for u in usage), 6),
                    conversation_file=f"metrics/{ex.run_id}_conversation.json",
                )
            rec.update(score=env.total_reward, **score_breakdown(env))
        finally:
            await env.close()
    rec["wall_s"] = round(time.time() - t0, 1)
    return rec


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--max-messages", type=int, default=10)
    ap.add_argument("--model", default="google/gemini-2.5-flash")
    ap.add_argument("--max-output-tokens", type=int, default=8192,
                    help="per-call output cap (0 = uncapped, the legacy behaviour)")
    ap.add_argument("--provider", action="append",
                    help="OpenRouter provider to prefer (repeatable), e.g. DeepInfra")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default="runs/smoke.jsonl")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout)], force=True)
    if args.dry_run:
        os.environ.setdefault("OPENROUTER_API_KEY", "dry-run-unused")  # client is built, never called
    elif not os.getenv("OPENROUTER_API_KEY"):
        sys.exit("OPENROUTER_API_KEY not set")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    for i in range(args.n):  # sequential on purpose: one validator per rollout
        before = None if args.dry_run else key_usage()
        rec = await one_rollout(i, args)
        if before is not None:
            await asyncio.sleep(5)  # usage endpoint lags a little
            rec["cost_usd_key_delta"] = round(key_usage() - before, 6)
        with open(args.out, "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"ROLLOUT {i}: score={rec.get('score')} memo={rec.get('memo_points')} "
              f"wall={rec['wall_s']}s cost={rec.get('cost_usd_reported')}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
