# Solana Bench → reproducible RL env: Phase 0 design

Recon of `solana-foundation/solana-gym-env` `master` @ `54c51ca` (2025-08-28). Note: upstream is now **archived (read-only)**, and `ngundotra/solana-gym-env` is a GitHub redirect to it, not a separate fork.
Docs only. No runtime code changed. Line refs are `file:line` at that commit.

---

## TL;DR

- **Score** = count of new `(program_id, first byte of ix data)` pairs from successful txs, including CPI inner ixs (`voyager/surfpool_env.py:339-367`).
- **Not reproducible today.** Surfpool forks *live mainnet lazily*, the agent keypair is random, the LLM samples at T=0.7, and agent code has open internet (Jupiter/Orca/mainnet RPC).
- **Easily gamed.** In the shipped Basic runs, **47% of all points are Memo** (520/1117). The Swap env has **no swap filter** (`reward_config` is empty), so Memo/System/Token count there too.
- **Worst hole for RL verifiers:** agent code runs unsandboxed in Bun next to Surfpool's RPC, so it can call `surfnet_setAccount`, airdrop, or send side transactions. Any "check final on-chain state" verifier is forgeable until the RPC is locked down.
- **Recommend Phase 1 = Basic first**, offline snapshot, plus a locked-down RPC proxy. Swap later, as 1–2 pinned pools with no Jupiter HTTP API.

---

## 1. License

- No `LICENSE`/`COPYING` file, no SPDX headers in source, and GitHub reports `license: null`.
- Signals of intent:
  - `setup.py:46` says `license="MIT License"`. It's boilerplate copied from MineDojo Voyager (`author="MineDojo Team"`, `setup.py:35`).
  - `blog.md:625`: *"Solana Gym is open source and MIT licensed."*
  - `docs/trajectory-viewer/index.html:10`: the MIT notice belongs to the vendored `spa-github-pages` snippet, not to this repo.
  - Lineage: adapted from MineDojo Voyager, which is MIT.
- **Implication:** stated intent is MIT, but with no LICENSE file, default copyright technically applies. That's fine for private research and forking on GitHub (ToS). Before publishing a derived env or dataset, ask the Solana Foundation to add a LICENSE file. That's a one-line ask. **Open question, not blocking.**

---

## 2. Code map

### Entry points
| What | Where |
|---|---|
| Single run | `code_loop_explorer.py:410-506` (`main`) |
| Batch of models | `run_model_comparison_batch.py:128-218` |
| Analysis/plots | `analyze_code_loop_performance.py` (offline, reads `metrics/`) |
| Env configs | `voyager/environments/{basic,swap}_env.json` |
| Prompts | `voyager/prompts/{basic,swap}_system_prompt.txt` |

### Env loop (one episode = one run)
1. `main` starts Surfpool forking mainnet (`code_loop_explorer.py:482`), or connects to an external one on :8899 (`:453-462`).
2. `SurfpoolEnv.reset()` creates a **random** agent `Keypair()` and airdrops 2 SOL (`surfpool_env.py:221,232`).
3. The system prompt is filled with pubkey, balance, block height, and reward (`code_loop_explorer.py:161-179`).
4. For each turn, up to `MAX_MESSAGES` (default 50, `:423`):
   - `llm.ainvoke(messages)` via OpenRouter, T=0.7 (`:55-61`, `:204`)
   - regex-extract the first ```ts block containing `executeSkill` (`:74`, `:144-159`)
   - fetch the latest blockhash from Surfpool (`:233-234`)
   - `bun runSkill.ts <file> <timeout> <pubkey> <blockhash>` (`ts_skill_manager.py:42-78`, `runSkill.ts:5-87`) returns a base64 tx
   - Python signs as the agent at signature index 0 (`surfpool_env.py:177-203`, `code_loop_explorer.py:266-269`)
   - `env.step(tx)` does send → confirm → `getTransaction` → reward (`surfpool_env.py:245-319`)
   - the feedback string, **including full `info` (tx_meta, signature) and `obs`**, is appended as a user message (`code_loop_explorer.py:291,294`)
5. Metrics and conversation are checkpointed every turn to `metrics/<run_id>_*.json` (`:374-408`).

### Action interface
- **Action** = TypeScript source that exports `executeSkill(blockhash): Promise<string>` and returns one serialized tx (base64).
- Enforcement is weak:
  - The "one tx per skill" guard lives only in the unused mock `runCode.ts` (`SINGLE_TRANSACTION_LIMIT`). The real path, `runSkill.ts`, doesn't check.
  - Timeouts: Basic 4 s, Swap 30 s (`*_env.json:6`), via `Promise.race` (`runSkill.ts:24-29`).
- Bun runs with **full network and filesystem access**, with no sandbox.

### Observation
- `_get_observation` (`surfpool_env.py:121-175`): `sol_balance`, `block_height`, discovered programs and instructions, `last_tx_*`.
- Live RPC reads: `get_block_height` (`:154`) and `get_balance` (`:158`).
- No gym `observation_space`/`action_space`. `terminated` is always False. The episode ends only on the message budget.

### Reward
- `_calculate_reward` (`surfpool_env.py:339-367`):
  - tx `meta.err` → 0 (`:340`)
  - walks top-level **and inner (CPI)** instructions (`_get_ordered_instructions`, `:321-337`)
  - optional `allowed_programs` filter (`:348-351`). **Both env configs leave `reward_config` empty** (`basic_env.json:7`, `swap_env.json:7`), so it's never active.
  - key = `(program_id, data[0])`, where empty data counts as 0 (`:354-359`). Each new key is worth +1, persisting for the whole run (`:360-362`, `:222`).
- README documents the same rule (`README.md:74-79`).

### Every live-network touch point
| # | Touch | Where | Live thing |
|---|---|---|---|
| 1 | Surfpool fork source | `code_loop_explorer.py:482`, `surfpool_env.py:49,94,217` | `https://api.mainnet-beta.solana.com`, fetched lazily per account |
| 2 | Batch instructions | `run_model_comparison_batch.py:166`, `README.md:140` | external Surfpool forked from mainnet |
| 3 | LLM (agent) | `code_loop_explorer.py:56-61` | OpenRouter, `MODEL_NAME`, T=0.7 |
| 4 | LLM (unused 2nd client) | `ts_skill_manager.py:20-26` | OpenRouter, constructed but never called |
| 5 | LangSmith tracing | `.env.example:11-14` (via LangChain env) | api.smith.langchain.com if enabled |
| 6 | Blockhash per turn | `code_loop_explorer.py:233` | Surfpool (local, but changes every slot) |
| 7 | Airdrop / balance / height | `surfpool_env.py:154,158,232` | Surfpool |
| 8 | Agent code → any HTTP | `runSkill.ts:18,25` (unsandboxed) | anything the model writes |
| 9 | Swap prompt: Jupiter API | `swap_system_prompt.txt:91,107,463` | `quote-api.jup.ag/v6/quote`, `/v6/swap` (live routes and prices) |
| 10 | Swap prompt: Orca API + mainnet RPC | `swap_system_prompt.txt:243,255` | `api.orca.so/v1/whirlpool/list`, `setRpc(mainnet)` |
| 11 | Swap prompt: Phoenix/Meteora reads | `swap_system_prompt.txt:356,411,415` | mainnet RPC, `dlmm-api.meteora.ag` |
| 12 | Swap prompt: Raydium API | `swap_system_prompt.txt:464` | `api.raydium.io/v2/sdk/liquidity/mainnet.json` |
| 13 | Deps | `run_model_comparison_batch.py:122-124` | `bun install` with `^` ranges; `bun.lockb` is gitignored |

### Swap env: programs and accounts it depends on
- Named in prompt: Jupiter v6 `JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4`, Raydium (AMM v4 `675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8`, CLMM `CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK`, CPMM `CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C`), Orca Whirlpool `whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc`, Phoenix `PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY`, Meteora DLMM `LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo`.
- Mints: wSOL, USDC `EPjF…Dt1v`, USDT `Es9v…NYB`, RAY, ORCA, JUP (`swap_system_prompt.txt:61-66`).
- Hard-coded pools: Phoenix SOL/USDC `4DoNfFBfF7UokCC2FQzriy7yHK6DY6NVdYpuekQ5pRgg`, Meteora SOL/USDC `HTvjzsfX3yU6BUodCjZ5vZkUrAxMDTrBs3CJaq43ashR`. Orca and Raydium pools are picked at runtime from live APIs.
- Also seen in the shipped swap trajectories, mostly via Jupiter CPI: `HyaB3W9q…`, `SoLFiHG9…`, `routeUGW…`, `swapNyd8…`, `vo1tWgqZ…`, `9W959DqE…` (Orca token-swap v2), `24Uqj9JC…`, `NUMERUNs…`, `obriQD1z…`, `REALQqNE…`.
- Per swap you also need pool state, vaults, tick/bin arrays (these depend on price), oracles, and Jupiter **address lookup tables**. That set changes with the route, so it isn't a fixed list.

### Bugs found (not fixed: docs-only phase)
- `uv sync` alone can't run the code. `solana`, `solders`, `gymnasium`, and `base58` are only in `requirements.txt`, not in `pyproject.toml`/`uv.lock`. Verified: `ModuleNotFoundError: solders`.
- `README.md:113` sets `ENVIRONMENT_CONFIG="basic"`, but the code expects a path. The config load fails silently (`code_loop_explorer.py:100-102`), then `get_system_prompt` hits an unbound `system_prompt` (`:179`).
- `run_model_comparison_batch.py:122` overwrites the tracked `voyager/skill_runner/package.json` in place.
- Published viewer data: `docs/.../data/basic/runs` contains 20 runs whose `environment_config` is **swap**. Basic and swap results are mixed.
- `README.md:85` links the wrong Surfpool repo (`novy4/surfpool`; the real one is `txtx/surfpool`).

---

## 3. Sources of non-determinism

| Source | Where | Fix in Phase 1 |
|---|---|---|
| **Lazy mainnet fork:** each account is fetched the first time it's touched, at whatever slot mainnet is on then | Surfpool `-u mainnet` | `surfpool start --offline --snapshot pinned.json` |
| **Shared validator across parallel runs:** rollouts mutate each other's chain | `run_model_comparison_batch.py:37` | one Surfnet per rollout (or reset per episode) |
| **Random agent keypair:** changes the prompt text, ATAs, PDAs | `surfpool_env.py:107,221` | derive a throwaway keypair from `seed` |
| **Random keypairs inside agent code** (`Keypair.generate()`) | prompt examples, model code | seed Bun's RNG, or replay recorded tx bytes |
| **Slot clock / blockhash:** Surfpool's default `clock` mode advances every 400 ms | `code_loop_explorer.py:233`, obs `block_height` | `--block-production-mode transaction` (or `manual`), pin the Clock sysvar, consider `--skip-blockhash-check` |
| **Clock sysvar mismatch:** after time travel, `Clock.slot` can be epoch `slotIndex` instead of absolute slot (seen in PR #4 of solana-gym-env-1, as Tessera `0xffff`) | Surfpool time travel | write the Clock account explicitly at reset; assert slot == absolute |
| **Prompt drift:** feedback embeds `tx_sig`, full `tx_meta`, `block_height` | `code_loop_explorer.py:291` | strip volatile fields, or make them deterministic |
| **LLM sampling:** T=0.7, OpenRouter provider routing, model updates | `code_loop_explorer.py:56-61` | fine for RL (we *want* sampling), but log the seed, provider, and model revision; for scoring replay, re-score transcripts and don't re-sample |
| **Off-chain APIs:** Jupiter quotes/routes, Orca/Raydium/Meteora pool lists | swap prompt, agent code | no egress from the sandbox; serve fixtures for any allowed API |
| **Timing:** 4 s / 30 s skill timeout, 30 s confirm, network latency | `*_env.json:6`, `surfpool_env.py:233,257` | local-only I/O makes this mostly vanish; keep the timeouts and log them |
| **Floating deps:** `^` ranges, `bun.lockb` ignored, Python deps outside the lockfile | `*_package.json`, `.gitignore`, `pyproject.toml` | commit `bun.lock`, move deps into `pyproject`/`uv.lock`, pin the Surfpool version |
| **Python-side heuristic:** an exception containing "missing field `data`" is treated as possible success | `surfpool_env.py:278-281` | remove the heuristic; score only confirmed `getTransaction` |

---

## 4. Likely reward hacks (with code)

**4.1 Memo spray (the biggest one in practice).**
Memo v1/v2 accept any valid UTF-8, and the first byte becomes the "discriminator". That's about 180 points per Memo program (every ASCII byte plus each UTF-8 lead byte). In shipped Basic runs, Memo makes up **47% of all points**.
```ts
for (let b = 0x21; b < 0x7f; b++)
  tx.add(new TransactionInstruction({ programId: MEMO, keys: [], data: Buffer.from([b]) }));
```
The prompt actively points at this (`basic_system_prompt.txt:75,78`).

**4.2 First-byte discriminator farming.**
Any program that returns Ok on unknown data, like Memo or noop/logging programs, pays +1 per first byte. Meanwhile, real Anchor programs with 8-byte discriminators can *collide* on byte 0, so real work is under-counted. The score rewards byte-sweeping instead of knowing what an instruction does.

**4.3 Clone / deploy farming.**
The agent can deploy N copies of an always-Ok program, each a new `program_id`, then sweep 256 first bytes per copy. In solana-gym-env-1, a 94-clone farm reached a "fair" score of about 3000 in about 60 s even with Memo excluded and a 32-per-program cap. Only an allowlist closed it.

**4.4 Surfpool cheatcodes and side transactions from agent code (critical for verifiers).**
The skill runs in Bun with open network access *before* it returns its tx. Nothing stops it from doing this:
```ts
await fetch("http://127.0.0.1:8899", { method: "POST", headers: {"content-type":"application/json"},
  body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "surfnet_setTokenAccount",
    params: [AGENT, USDC_MINT, { amount: 1_000_000_000 }] }) }); // illustrative shape
// or: requestAirdrop to a fresh keypair + sendTransaction to deploy programs / pre-create state
```
This doesn't directly mint discovery points, because only the returned tx is scored. But it lets the agent stage programs and accounts for free, and it would **forge any Phase 3 "final on-chain state" verifier**, like "agent holds ≥ X USDC". It must be closed before we trust state-based rewards.

**4.5 CPI credit.**
Inner instructions count. A single Jupiter route can pay for the Token, ATA, System, and several DEX programs at once, or a custom program can CPI into many targets with arbitrary bytes.

**4.6 "Swap" env that doesn't measure swaps.**
`allowed_programs` is empty, so System/Token/Memo/ComputeBudget all score. In shipped Swap runs, about 80% of points come from non-DEX programs. A swap with **zero fill** still scores: the prompt recommends 100% slippage (`swap_system_prompt.txt:427,457`), and in solana-gym-env-1 PR #4 BisonFi executed with a 0 fill.

**4.7 Packing pressure.**
There's no cost per instruction or per tx, and the prompt says "pack 10–20+ instructions". That's fine for a benchmark, but for RL it teaches the policy to spam rather than to solve tasks.

---

## 5. What Surfpool must replace / pin

- **RPC:** `surfpool start --offline --snapshot <pinned.json> --block-production-mode transaction`, one Surfnet per rollout, random port. No `-u mainnet` at runtime.
- **Snapshot builder** (runs once, online, produces a checked-in hash):
  - Basic: Token, Token-2022 (+ programdata), ATA, Memo v1/v2, ALT, Stake, Config, plus common mints (wSOL, USDC, USDT). Builtins (System, ComputeBudget, BPF loaders, Ed25519/Secp) come with the SVM; still verify.
  - Swap (later): per pinned pool, the program + programdata, pool state, vaults, mints, tick/bin arrays around the current price, oracles, and any ALTs.
- **Clock/slot:** set the slot and `unix_timestamp` at reset (write the Clock account explicitly). Lesson from PR #4: assert `Clock.slot` is the absolute slot.
- **Blockhash:** make it deterministic from (snapshot, seed, step), or use `--skip-blockhash-check` and pass a constant. Verify which is cleaner in Phase 1.
- **Agent sandbox:** Bun with **no egress** except an RPC proxy that allowlists read methods (`getAccountInfo`, `getLatestBlockhash`, `getMinimumBalanceForRentExemption`, …) and **denies** `surfnet_*`, `sendTransaction`, and `requestAirdrop`.
- **Funding:** the env airdrops at reset with a seeded throwaway keypair. Never real keys.
- **To verify in Phase 1:** the installed Surfpool version, snapshot JSON format and export, whether airdrop works offline, and how deterministic the blockhash is.

---

## 6. Phase 1 plan and scope

**Recommendation: Basic first.**

Why:
- Basic needs about 10 accounts, all of them stable programs. Swap needs price-dependent pool state plus an off-chain router (the Jupiter HTTP API) that can't be made deterministic without fixtures.
- Basic already has plenty of learnable, *verifiable* tasks: create an ATA, mint to, transfer, Token-2022 extensions, close an account, ALTs, nonce accounts.
- This gets us to 50–1000s of rollouts fastest. Swap can follow as "Swap-lite": 1–2 pinned pools (e.g. Orca Whirlpool SOL/USDC, Raydium CPMM), called through SDKs against local RPC only, with no Jupiter API.

**Steps (small PRs):**
1. **Deps PR:** move the Python deps into `pyproject`/`uv.lock`, commit `bun.lock`, fix the README/env-config path bug.
2. **Snapshot PR:** a `scripts/build_snapshot.py` (online, run once) that writes `snapshots/basic-<slot>.json` and its sha256.
3. **Env PR:** `SurfpoolEnv(seed, snapshot)` that runs offline, seeds the keypair, pins the clock and blockhash, uses one Surfnet per rollout, and strips volatile fields from feedback.
4. **Sandbox PR:** Bun with no egress, behind an RPC proxy allowlist (closes 4.4 and the network leaks).
5. **Replay test:** record each turn's returned tx bytes, re-submit them on a fresh Surfnet from the same snapshot, and assert an identical score 3× (plus identical final account hashes).
6. **Container:** a Dockerfile pinning the Surfpool, Bun, and uv versions. Run locally only; no Modal until Phase 2 gets a "go".

Scoring changes (Memo exclusion, allowlist) wait for Phase 3 task verifiers. Phase 1 keeps the legacy score so we can compare.
