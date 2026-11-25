# DECISIONS

One line per decision + why. Newest at bottom.

- 2026-11-25: Base the work on upstream @54c51ca, not `solana-gym-env-1`, because the old repo carries Memo/allowlist score hacks; start clean, read it only for lessons.
- 2026-11-25: `ngundotra/solana-gym-env` turned out to redirect to the archived upstream (no push). Paused before creating a new repo; Noah picks where it lives.
- 2026-11-25: Phase 0 is docs-only (DESIGN/STATUS/DECISIONS), so review is cheap and nothing runtime changes before the design is agreed.
- 2026-11-25: Phase 0 ran on Grok Bot's own computer via `gh`, because the Cursor cloud agent couldn't see the repo yet; reversible, same PR flow.
- 2026-11-25: PRs target Noah's own repo only, never upstream (which is archived anyway).
- 2026-11-25: Treat license as "intended MIT, unconfirmed"; OK for research, ask upstream to add LICENSE before publishing derived env/data.
- 2026-11-25: Recommend Basic-first for Phase 1: ~10 stable accounts vs. price-dependent pools + live Jupiter API for Swap.
- 2026-11-25: Keep legacy score in Phase 1 (for comparison); fix scoring via Phase 3 task verifiers, not by patching the discovery metric again.
- 2026-11-25: Replay test will re-submit recorded tx bytes (not re-run model code), because agent code calls Keypair.generate() and would differ each run.
- 2026-11-25: Repo home is `ngundotra/solana-bench-rl` (new public repo, not a GitHub fork) because upstream `solana-foundation/solana-gym-env` is archived/read-only and `ngundotra/solana-gym-env` redirects there.
- 2026-11-25: Seeded history omits `.github/workflows/*` (Foundation CI + trajectory-viewer Pages deploy) because the `gh` token lacks the `workflow` scope and GitHub rejected a verbatim push. File contents otherwise match upstream `@54c51ca`. Restore later if needed.
- 2026-11-25: Smoke model = `google/gemini-2.5-flash` (repo default, $0.30/M in, $2.50/M out), so the baseline matches upstream's default and stays cheap.
- 2026-11-25: Smoke budget = 10 messages/rollout (upstream default 50): context grows every turn, so 10 keeps the worst case < $0.25/rollout; enough to see failure modes.
- 2026-11-25: Rollouts run sequentially, one fresh Surfpool per rollout on :8899, refusing to start if the port is busy, so no two rollouts share chain state.
- 2026-11-25: Basic env gets its own Bun dir (`voyager/environments/basic_runtime`, committed `bun.lock`) instead of overwriting the tracked swap `package.json` like the batch script does.
- 2026-11-25: Fixed `confirm_transaction(..., 30.0)`: the 3rd arg is the *poll interval*, so every tx slept 30 s. Per-tx latency went from ~30 s to <1 s.
- 2026-11-25: New `--max-output-tokens` (default 8192, 0 = legacy uncapped) after a 57K-token runaway generation ate 44% of smoke spend. The recorded smoke run was uncapped.
- 2026-11-25: Spend is measured two ways: per-call `usage.cost` from OpenRouter (logged per turn) and the key's total usage (authoritative for STATUS).
