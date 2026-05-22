# PRD: Multi-source Micro SaaS opportunity signals

## Goal
Expand Micro SaaS Radar beyond HN and Reddit OAuth by adding free-first discovery sources and optional TrustMRR market-validation data.

## Requirements
- Add Reddit public JSON fallback with top-comment context when OAuth secrets are absent or unavailable.
- Add GitHub issue/discussion-style search via GitHub Search API with optional token.
- Expand AnySearch from Reddit-only fallback to multi-source search covering Reddit, X/Twitter, and GitHub web results.
- Add optional TrustMRR official API source gated by TRUSTMRR_API_KEY.
- Keep the report focused on Micro SaaS opportunity signals, not generic news.
- Preserve existing CLI behavior and reports.

## Non-goals
- Do not scrape private/authenticated X pages.
- Do not require paid APIs for the default workflow.
- Do not replace the existing HTML report design in this pass.

## Acceptance Criteria
- Existing tests pass.
- New parsers/heuristics have focused unit coverage.
- Running with skip-LLM still completes without new secrets.
- Missing TrustMRR/GitHub tokens do not fail the pipeline.

