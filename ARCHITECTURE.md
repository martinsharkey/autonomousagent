# Council Architecture

## Overview

The autonomous council is a 3-agent self-evolving system with layered governance, zero-cost operation, and safe mutation capabilities. All decisions require unanimous consensus.

---

## Agent Roles

### Autobot
- **Role**: Orchestrator, security auditor, operator interface
- **Responsibilities**:
  - Evaluate mutations for security risks (prompt injection, privilege escalation, unauthorized access)
  - Cast security-focused votes on proposed mutations
  - Provide operator interface for manual oversight
  - Coordinate council activities
- **Voting Focus**: Security audit, access control, malicious patterns

### Alpha (Alpha Evaluator)
- **Role**: Mission alignment evaluator, voting member
- **Responsibilities**:
  - Evaluate mutations for mission alignment (Pillars 1-5)
  - Assess test readiness before implementation
  - Cast approval/rejection votes based on alignment criteria
  - Verify mutations serve core objectives
- **Voting Focus**: Mission alignment, strategic value, test readiness

### Beta (Beta Worker)
- **Role**: Feasibility evaluator, worker, voting member
- **Responsibilities**:
  - Evaluate mutations for syntax correctness and code compatibility
  - Assess implementation feasibility
  - Verify test coverage adequacy
  - Execute approved mutations
- **Voting Focus**: Technical feasibility, implementation risk, compatibility

---

## Decision Making

### Unanimous Consensus
- All mutations require **unanimous approval** (all 3 agents must vote APPROVE)
- No single agent can override the voting requirement
- Deadlock scenarios escalate to human operator
- Consensus is checked after each agent casts their vote

### Voting Flow
1. Mutation proposed by any council agent
2. All three agents evaluate independently
3. If unanimous approve -> mutation proceeds to implementation
4. If any reject -> mutation is rejected and logged
5. If deadlock -> operator override required

---

## Mutation Pipeline

### 1. Proposal
- Agent identifies opportunity for improvement
- Creates mutation with Pillar classification (1-5)
- Quality score calculated (alignment, gain, risk, testability)
- Mutations with score < 60 are automatically rejected

### 2. Quality Scoring
- Alignment (40%): How well does it serve its mission pillar?
- Performance Gain (30%): Will it improve metrics?
- Risk Mitigation (20%): How safe is it to evaluate?
- Testability (10%): Can we safely test it?

### 3. Consensus Voting
- All three agents receive proposal
- Each agent evaluates from their specialized perspective
- Votes recorded with confidence scores and reasoning

### 4. Implementation
- Approved mutations are versioned in config store
- Evaluation suite runs against new version
- Automatic promotion if score improves within tolerance
- Automatic rollback if score regresses

### 5. Tracking
- MUTATIONS_ROADMAP.md updated with all proposed/approved/rejected mutations
- Quality scores visible in roadmap
- Implementation results logged with metrics

---

## Mission Pillars

Every mutation must serve one of five core mission pillars:

1. **Recursive Self-Evolution**: Gap analysis -> implement -> validate -> promote/rollback. Continuous self-improvement.
2. **Autonomous Resource Optimization**: Prefer free-tier inference. Cloud-first with failover. No single provider dependency.
3. **Model Agnosticism**: Support 20+ cloud providers. Failover and load balancing. No hard dependencies.
4. **Durable Local State**: Goals, configs, memory, audit logs persisted. SQLite + checkpoints. Recover from crashes.
5. **Companion Alignment**: Telegram interface + human steering. Operator override. Transparent reporting.

---

## System Limitations

### What the Council CANNOT Do
- Override unanimous voting requirement
- Modify core governance rules without human approval
- Access resources not provisioned in the current environment
- Deploy to unapproved infrastructure without evaluation
- Bypass HMAC security requirements
- Make decisions without consulting all council members
- Propose mutations that do not align with mission pillars

### Technical Constraints
- Mutations are limited to configurable parameters (temperature, max_retries, system_prompt)
- All mutations require evaluation before promotion
- Config changes require council approval
- Critical functions require HMAC signatures
- Rollback is automatic if new version underperforms

---

## Infrastructure

- **Primary Entry Point**: `council_daemon.py`
- **Language**: Python 3.12+
- **State Persistence**: SQLite + JSON checkpointer
- **LLM Router**: Cloud-first with Ollama fallback
- **Telegram Interface**: Operator commands (/who, /status, /goal, /approve, /reject, /stop, /help)
- **Audit Logging**: HMAC-signed events in governance/audit_log.py
- **Version Control**: Git-based mutation tracking with automatic commits

---

## Security Model

- All mutations are HMAC-signed before storage
- Config changes require unanimous council approval
- Critical operations logged with timestamps and agent attribution
- Operator override available but requires explicit rationale
- Public repository contains architecture only; implementation details in private documentation

---

## How to Run

```bash
# Start autonomous daemon (limited autonomy)
python council_daemon.py --interval 60 --autonomy limited

# Run test mode (3 cycles)
python council_daemon.py --test --autonomy safe

# Check health
python council_daemon.py --health

# Create a goal
python council_daemon.py --goal "Write a hello-world script"
```

---

## Evolution Cycle

1. **Goal Creation**: Human or system creates goal with priority
2. **Execution**: Council agents work toward goal
3. **Evaluation**: Results scored against success criteria
4. **Curiosity**: Poor metrics trigger exploration goals
5. **Mutation**: System proposes improvements aligned with mission pillars
6. **Consensus**: All agents vote on proposed mutations
7. **Implementation**: Approved mutations applied and evaluated
8. **Promotion/Rollback**: New version promoted if improved, otherwise rolled back
9. **Learning**: Results feed back into scoring and future proposals

---

*This document is maintained by the council and updated as the architecture evolves.*
