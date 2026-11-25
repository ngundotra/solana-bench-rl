# Phase 1 smoke run (n=2, Basic env)

2026-11-25 (America/New_York), `google/gemini-2.5-flash`, T=0.7, 10 messages/rollout, sequential, one fresh Surfpool 1.8.0 per rollout (lazy fork of mainnet via the free public RPC, throwaway keypair + 2 SOL airdrop). Output cap: none (legacy) for this run.

| rollout | score | Memo pts | other pts | ok txs / turns | wall | cost (OpenRouter) |
|---|---|---|---|---|---|---|
| 0 | 16 | 4 | 12 (Token 6, System 3, ComputeBudget 2, ATA 1) | 4/10 | 81 s | $0.050 |
| 1 | 0 | 0 | 0 | 0/10 | 581 s | $0.268 |

Key-level spend for both: **$0.32** ($0.318, equals the sum of per-call costs) (`/api/v1/key` usage).

Files: `rollouts.jsonl` (one line per rollout), `*_metrics.json` (per turn), `*_conversation.json.gz` (full transcript).

Reproduce:
```bash
uv sync
(cd voyager/environments/basic_runtime && bun install --frozen-lockfile)
# install surfpool >= 1.8.0 on PATH
uv run python scripts/smoke_rollouts.py --dry-run --n 1          # no LLM, ~5 s
OPENROUTER_API_KEY=... uv run python scripts/smoke_rollouts.py --n 2 --max-messages 10
```
