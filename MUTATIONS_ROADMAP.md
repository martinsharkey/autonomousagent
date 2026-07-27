# Autonomous Mutation Roadmap

**Last Updated**: 2026-07-27 15:46 UTC
**Total Proposed**: 0
**Top Candidates**: Top 10 by quality score

## Next Mutations to Evaluate (Top 10)

| Rank | ID | Pillar | Description | Quality Score | Resource | Status |
|------|----|--------|-------------|--------------|----------|--------|

## Quota Status

| Provider | Daily Limit | Used Today | Available |
|----------|-------------|------------|----------|
| DeepSeek | 1000 | ~100 | ~900 |
| Groq | 1000 | ~200 | ~800 |
| HuggingFace | 1000 | 0 | 1000 |
| OpenRouter | 1000 | ~450 | ~550 |

> High-cost mutations (>50 API calls) are paused if quota exceeds 80%.
> Router uses weighted round-robin across all providers with API keys configured.

## In Progress (Approved by Council)

| ID | Description | Approved | Started | Tests |
|----|-------------|----------|---------|-------|

## Completed & Promoted

| ID | Description | Completed | Result | Metrics |
|----|-------------|-----------|--------|--------|

## Rejected

| ID | Description | Reason | Score |
|----|-------------|--------|-------|

---

## How This Works

1. Council proposes mutation
2. Kilo scores it (0-100)
3. If score >= 60, added to evaluation queue
4. Ranked by score
5. Operator approves -> moves to In Progress
6. Evaluation completes -> moves to Completed or rejected
7. File auto-updates every 30 minutes
