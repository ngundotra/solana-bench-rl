# STATUS

**Phase:** 1 (offline env), smoke test done ✅. PR open for review
**Repo:** [ngundotra/solana-bench-rl](https://github.com/ngundotra/solana-bench-rl)
**Spend to date:** **$0.32** of $100 (OpenRouter, n=2 smoke run)

## Done
- Phase 0 recon → `docs/DESIGN.md` (PR #1)
- Env boots on Surfpool 1.8.0; dry run (no LLM) scores 1 Memo pt in ~5 s
- n=2 baseline, gemini-2.5-flash, 10 msgs: scores **16** and **0**
- Fixed 6 bugs that blocked or slowed runs (deps, config, Surfpool 1.8 compat ×2, 30 s/tx sleep, no-code crash)

## Learned
- Rollout 1 died on turn 1: a 57K-token runaway generation (7 min, 44% of spend), then 9 turns of apologies, 0 txs. Now capped at 8K output tokens
- Rollout 0: 4 of 16 pts from Memo (different first letters), 2 free ComputeBudget pts
- Top failure: TS type errors (BigInt vs number), not Solana logic

## Blocked
- Nothing. Modal token needed only at Phase 2

## Next decision for Noah
- Merge PR #1 + this PR, then continue Phase 1: pinned offline snapshot + seeded env? Reply "go phase 1"

## Next up
1. Snapshot (offline) + seeded keypair  2. Sandbox agent code  3. Replay test ×3
