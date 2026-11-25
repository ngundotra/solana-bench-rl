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
