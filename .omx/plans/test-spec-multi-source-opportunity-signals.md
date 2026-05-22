# Test Spec: Multi-source Micro SaaS opportunity signals

## Checks
- Unit tests cover AnySearch URL source classification for Reddit, X/Twitter, and GitHub.
- Unit tests cover GitHub issue item conversion and signal extraction.
- Unit tests cover TrustMRR item conversion and heuristic analyzer treatment.
- Smoke run uses `python3 main.py --skip-reddit --skip-trends --skip-llm --max-analyze 5 --skip-trustmrr`.

## Risk Areas
- Upstream APIs can rate-limit or change response shapes.
- TrustMRR API requires a user-provided key.
- X/Twitter results through web search can be sparse and should stay best-effort.

