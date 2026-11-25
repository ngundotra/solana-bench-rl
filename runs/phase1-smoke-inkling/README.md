# Phase 1 smoke run: Inkling 2 Mini (n=2, Basic env)

2026-11-25 (America/New_York). OpenRouter `thinkingmachines/inkling-2-mini` (Thinking Machines' looped transformer, 26.4B total / 3.4B active), provider pinned to DeepInfra ($0.075/M in, $0.30/M out), T=0.7, 10 messages/rollout, output cap 16,384 tokens (the model reasons, and reasoning counts toward the cap). Same setup as `../phase1-smoke/`: sequential runs, a fresh Surfpool 1.8.0 per rollout, throwaway keypair.

| rollout | score | Memo pts | other pts | ok txs / turns | turns with no code | wall | cost |
|---|---|---|---|---|---|---|---|
| 0 | 13 | 2 | 11 (Token-2022 4, Token 3, System 2, ComputeBudget 2) | 4/10 | 1 | 164 s | $0.0148 |
| 1 | 3 | 1 | 2 (System 1, ComputeBudget 1) | 1/10 | 9 | 271 s | $0.0248 |

Spend for both rollouts: **$0.0396** (key usage delta). That's about 8× cheaper than Gemini 2.5 Flash's $0.318. Three tiny provider-check calls cost about $0.0002.

Main failure: **missing code fences**. Content often says "…instructions.typescriptLet me…" and then repeats one sentence until it hits the 16K cap (4 of 20 calls). In rollout 1, 9 of 10 turns had no ```typescript block. A short standalone prompt gets proper fences from DeepInfra, PrimeIntellect and Relace alike, so the problem shows up only in the long agent context. Hypothesis to test next: the code block lands in the reasoning channel, which LangChain drops.
