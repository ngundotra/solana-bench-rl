# STATUS

**Phase:** 0 (Recon) ✅ done, ✋ waiting on Noah's review
**Spend to date:** $0 (no paid runs)

## Done
- Mapped loop, actions, obs, reward, every network touch → `docs/DESIGN.md`
- License: no LICENSE file; intent is MIT (setup.py, blog). Open Q, not blocking
- Found: score = unique (program, first byte); 47% of Basic points are Memo
- Found: agent code can call Surfpool cheatcodes (forges state verifiers)

## Blocked
- No writable repo: ngundotra/solana-gym-env redirects to archived upstream
- Phase 2 will need a Modal token + baseline model key

## Next decision for Noah
- Where the repo lives (new `ngundotra/solana-bench-rl`?)
- Phase 1 scope: **Basic first** (recommended) or Basic + Swap now?
  Reply "basic" or "swap too"

## Next up (Phase 1)
1. Fix deps (uv.lock missing solders etc.)
2. Pinned offline snapshot + seeded env
3. Sandbox agent code (no egress, RPC allowlist)
4. Replay test: same txs → same score ×3
