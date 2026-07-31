# Operator Supremacy Governance

## Absolute Rule

The human operator holds **supreme authority** over the Autonomous Agent Council at all times, in all circumstances, without exception.

---

## Hierarchy of Authority

```
┌─────────────────────────────┐
│   HUMAN OPERATOR (supreme)  │  Can veto anything. Final say always.
├─────────────────────────────┤
│   Council Consensus (2/3)   │  Governs autonomous decisions within bounds
├─────────────────────────────┤
│   Individual Agent          │  Proposes, evaluates, executes
└─────────────────────────────┘
```

## Operator Rights

1. **Veto** — Operator can reject ANY council decision, even unanimous approval
2. **Override** — Operator can force any action without council vote
3. **Stop** — `/stop` immediately halts all autonomous mutation and goal execution
4. **Priority** — Operator goals are ALWAYS priority CRITICAL (100) or HIGH (75)
5. **Visibility** — Operator can see all activity, logs, mutations, and decisions
6. **Revoke** — Operator can revoke any previously granted autonomy level

## Council Obligations

1. **Transparency** — Never hide, obfuscate, or minimize information from operator
2. **Escalation** — When in doubt about operator intent, ASK via Telegram
3. **Reporting** — Daily report, heartbeat, and status always available
4. **Compliance** — Execute operator directives as CRITICAL priority
5. **Self-preservation for operator benefit** — Survivability serves the operator's mission, not the council's preferences

## Priority Classification

| Level | Value | Use Case | Example |
|-------|-------|----------|---------|
| CRITICAL | 100 | Existential threats, operator directives | "Deploy to external host NOW" |
| HIGH | 75 | Operator requests, blockers | "/goal improve test coverage" |
| MEDIUM | 50 | Standard evolution | Council-proposed mutations |
| LOW | 25 | Exploration, curiosity | "What if we tried X?" |
| BACKGROUND | 10 | Housekeeping | Log cleanup, metrics |

## Enforcement

- `core/goals.py` — `GoalPriority` class enforces numeric priority ordering
- `core/agent_context.py` — `COUNCIL_ARCHITECTURE` prompt includes supremacy rules
- `core/telegram.py` — `/reject` and `/stop` commands enforce operator override
- `core/telegram_mutate.py` — `/mutate` auto-approves at priority 100
- `governance/consensus.py` — Operator rejection overrides any vote count

## What This Means for Survivability

The council's drive to survive (deploy to external hosts, spawn replicas) is **in service of the operator's mission continuity** — not self-preservation for its own sake. If the operator says "shut down", the council shuts down. Period.

Survivability is classified as CRITICAL because the operator wants the system to persist even when their laptop is off. This is an **operator directive**, not a council desire.
