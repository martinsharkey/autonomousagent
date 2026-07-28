# Claude Validation Checklist

## WHAT I'M LOOKING FOR

If code works, I expect to see:

### Cycle 1:
- [ ] Proposer generates mutation (config param or file change)
- [ ] Validator checks it (valid mission pillar, params exist, not duplicate)
- [ ] Council votes (Autobot, Alpha, Beta all vote)
- [ ] Implementation (file created or config updated)
- [ ] Tests run (pytest passes)
- [ ] Metrics collected (success_rate, latency, etc)
- [ ] Promoted to main (or rolled back if failed)
- [ ] Telegram notified (only if promoted)
- [ ] Proposer learns (stores result for next proposal)

### Cycle 2:
- [ ] Proposer generates DIFFERENT mutation (learned from cycle 1)
- [ ] Repeat...

## BROKEN STATE INDICATOR

If I see:

Cycle 1-10:
- [ ] Proposer generates mutation
- [ ] Validator rejects as duplicate
- [ ] No voting
- [ ] No implementation
- [ ] No progress

Then something is broken.

## Evidence Collected

_To be filled by running verification commands._
