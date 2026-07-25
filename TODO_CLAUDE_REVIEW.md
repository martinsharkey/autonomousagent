# Claude Review Action Plan - TODO List

**Date**: July 25, 2026  
**Source Documents**: 5 Claude Review documents  
**Status**: All 16 tasks [x] Complete  
**Total Action Items**: 16 major tasks

---

## EMERGENCY FIXES (Critical - Do Today)

### Task 1: Fix Consensus Voting to Unanimous
**Source**: IMMEDIATE_ACTION_PLAN.md (lines 11-38), AUTONOMOUSAGENT_QA_AUDIT.md (lines 95-130)  
**Priority**: CRITICAL  
**Time**: 5 minutes  
**Dependencies**: None  
**Status**: [ ] Pending

**Problem**: Current code uses 2/3 majority instead of unanimous consent  
**File**: `governance/consensus.py`, line 36

**Current (WRONG)**:
```python
if approvals >= len(self.agents) * 2 / 3:  # ? 2/3 MAJORITY
```

**Required (CORRECT)**:
```python
if all(v == ""approve"" for v in votes.values()):  # ? UNANIMOUS
```

---

### Task 2: Expand AgentState Schema
**Source**: IMMEDIATE_ACTION_PLAN.md (lines 42-98), BUILD_PRIORITY_ROADMAP.md (lines 10-76)  
**Priority**: CRITICAL  
**Time**: 30 minutes  
**Dependencies**: None  
**Status**: [x] Complete

**File**: `core/state.py`

**Add these fields to AgentState TypedDict**:
- `active_mutation_id: Optional[str]`
- `proposed_mutation_code: Optional[str]`
- `mission_rationale: Optional[str]`
- `council_votes: Dict[str, Optional[bool]]`
- `mission_scores: Dict[str, float]`
- `operator_override: Optional[str]`
- `operator_override_rationale: Optional[str]`
- `operator_override_timestamp: Optional[str]`
- `escalation_reason: Optional[str]`
- `requires_operator_approval: bool`
- `proposed_version: Optional[str]`
- `current_version: str`
- `rollback_pending: bool`
- `rollback_target_version: Optional[str]`
- `rollback_approved: bool`
- `rollback_reason: Optional[str]`

---

## PHASE 1: Foundation (This Week - Days 1-7)

### Task 3: Refactor Agents to Actually Vote
**Source**: IMMEDIATE_ACTION_PLAN.md (lines 103-187), BUILD_PRIORITY_ROADMAP.md (lines 251-422)  
**Priority**: HIGH  
**Time**: 3-5 days  
**Dependencies**: Task 1, Task 2  
**Status**: [x] Complete

**Files**: `agents/autobot.py`, `agents/alpha_evaluator.py`, `agents/beta_worker.py`

**Requirements**:
- Each agent must call MLLM with clear voting prompt
- Each agent must log its vote with rationale
- State must be updated with votes
- Consensus check triggers after all votes in
- No LLM involved in routing (pure logic only)

**Voting Models**:
- Autobot: Phi-4-Mini (security audit)
- Alpha: Qwen2.5-7B (mission) + DeepSeek-Coder-6.7B (tests)
- Beta: Feasibility analysis

---

### Task 4: Build Immutable Version Store
**Source**: IMMEDIATE_ACTION_PLAN.md (lines 190-281), BUILD_PRIORITY_ROADMAP.md (lines 78-151)  
**Priority**: HIGH  
**Time**: 2-3 days  
**Dependencies**: Task 2  
**Status**: [x] Complete

**New File**: `core/version_store.py`

**Requirements**:
- Immutable code version repository
- SHA256 hashes for each version
- Parent lineage tracking
- Cannot overwrite existing versions
- Manifest file (JSON) tracking all versions
- Rollback capability

**Key Methods**:
- `save_version(code, member_id, mutation_id, parent_version) -> str`
- `get_version(version_id) -> str`
- `get_history(member_id) -> List[Dict]`

---

### Task 5: Build Decision Logger
**Source**: IMMEDIATE_ACTION_PLAN.md (lines 284-331), BUILD_PRIORITY_ROADMAP.md (lines 153-249)  
**Priority**: HIGH  
**Time**: 1 day  
**Dependencies**: None  
**Status**: [x] Complete

**New File**: `governance/decision_logger.py`

**Requirements**:
- SQLite-based append-only log
- Every vote logged with model + confidence
- Every operator override logged with rationale
- Every rollback logged with reason + approval
- Query by mutation_id for full audit trail

**Schema**:
```sql
CREATE TABLE decision_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    mutation_id TEXT,
    council_member TEXT,
    model_used TEXT,
    vote TEXT,
    confidence REAL,
    metadata JSON,
    operator_override TEXT,
    operator_rationale TEXT
)
```

---

### Task 6: Build Operator Interface (Telegram Bot)
**Source**: IMMEDIATE_ACTION_PLAN.md (lines 334-418), OVERRIDE_APPROVAL_ESCALATION.md (lines 419-513)  
**Priority**: HIGH  
**Time**: 2-3 days  
**Dependencies**: Task 2  
**Status**: [x] Complete

**New File**: `core/operator_interface.py`

**Requirements**:
- Telegram bot with inline buttons (APPROVE/HOLD/REJECT)
- Callback handler for button clicks
- Decision logging with timestamp
- Autobot can read operator override
- Timeout handling (1 hour default)

**Button Actions**:
- ? APPROVE: Proceed with mutation
- ? HOLD: Pause and wait for rationale
- ? REJECT: Override council decision

---

## PHASE 2: MLLM Integration (Week 2 - Days 8-14)

### Task 7: Build MLLM Registry and Loader
**Source**: MLLM_CURATION_STRATEGY.md (lines 1-464), BUILD_PRIORITY_ROADMAP.md (lines 425-442)  
**Priority**: MEDIUM  
**Time**: 2-3 days  
**Dependencies**: Task 3  
**Status**: [x] Complete

**New File**: `models/mllm_registry.py`

**Model Selection**:
| Decision Type | Model | Memory | Purpose |
|---------------|-------|--------|---------|
| Mission alignment | Qwen2.5-7B | 3.8GB | Voting on mission fit |
| Test analysis | DeepSeek-Coder-6.7B | 3.6GB | Parse test logs |
| Security audit | Phi-4-Mini | 2.5GB | Detect injection |
| Rollback assessment | Qwen2.5-14B | 7.5GB | Schema reasoning |
| Decision logging | Structured JSON | 0MB | Deterministic logging |

**Requirements**:
- LRU eviction to stay under 8GB VRAM
- Sequential model loading
- Every inference logged (tokens + latency)
- Models swappable without code change

---

### Task 8: Build Rollback Engine
**Source**: OVERRIDE_APPROVAL_ESCALATION.md (lines 132-237), MLLM_CURATION_STRATEGY.md (lines 269-330)  
**Priority**: MEDIUM  
**Time**: 2-3 days  
**Dependencies**: Task 4  
**Status**: [x] Complete

**File**: `core/rollback.py` (enhance existing)

**Requirements**:
- Rollback safety assessment using Qwen2.5-14B
- State schema comparison (current vs target)
- Data loss risk detection
- Operator approval required (always)
- Restore code + state from version X

**Safety Check Output**:
```json
{
  ""rollback_safe"": boolean,
  ""data_loss_risk"": ""NONE"" | ""MINOR"" | ""CRITICAL"",
  ""fields_lost"": [...],
  ""compatibility_issues"": [...],
  ""operator_approval_required"": boolean
}
```

---

### Task 9: Build Unified Notifier
**Source**: OVERRIDE_APPROVAL_ESCALATION.md (lines 603-656)  
**Priority**: MEDIUM  
**Time**: 2-3 days  
**Dependencies**: Task 6  
**Status**: [x] Complete

**New File**: `interfaces/unified_notifier.py`

**Requirements**:
- Send to BOTH Telegram and VS Code chat simultaneously
- Accept response from either interface (race condition handling)
- Log which interface operator used
- Keep both interfaces in sync

---

## PHASE 3: Storage & Archival (Week 3 - Days 15-21)

### Task 10: Build Storage Tracker
**Source**: OVERRIDE_APPROVAL_ESCALATION.md (lines 257-414)  
**Priority**: MEDIUM  
**Time**: 2-3 days  
**Dependencies**: Task 5  
**Status**: [x] Complete

**New File**: `storage/storage_tracker.py`

**Requirements**:
- Track all writes by category (decision_log, test_output, code_version)
- Calculate usage percentage
- Alert at 80% capacity
- Suggest archival candidates (retainable + 30 days old)

**Categories**:
- decision_log: Hot 90 days, archive S3, delete 1 year
- test_output: Hot 14 days, archive S3, delete 90 days
- code_version: Hot forever, archive Glacier

---

### Task 11: Build Escalation Handler
**Source**: OVERRIDE_APPROVAL_ESCALATION.md (lines 92-129, 240-254)  
**Priority**: MEDIUM  
**Time**: 1-2 days  
**Dependencies**: Task 6  
**Status**: [x] Complete

**New File**: `core/escalation_handler.py`

**Escalation Conditions**:
| Condition | Severity | Auto-Action |
|-----------|----------|-------------|
| Security subsystem mutation | HIGH | Hold promotion |
| Council deadlocked >30 min | MEDIUM | Escalate to operator |
| Test results ambiguous (70-85%) | MEDIUM | Flag for review |
| Regression detected | CRITICAL | Propose rollback |
| Prompt injection flagged | CRITICAL | BLOCK immediately |
| Storage >80% | MEDIUM | Alert for archival |
| Model accuracy <75% | MEDIUM | Alert, continue |

---

## PHASE 4: Testing (Week 4 - Days 22-28)

### Task 12: Unit Tests for Unanimous Voting
**Source**: BUILD_PRIORITY_ROADMAP.md (lines 479-551)  
**Priority**: MEDIUM  
**Time**: 3 days  
**Dependencies**: Task 1, Task 2, Task 3  
**Status**: [x] Complete

**New File**: `tests/test_council_unanimous_voting.py`

**Test Cases**:
1. `test_unanimous_approval_triggers_tests()`: All YES ? run tests
2. `test_dissent_escalates_to_operator()`: Mixed votes ? escalate
3. `test_rollback_requires_operator_approval()`: Rollback blocks until approved
4. `test_operator_override_logged()`: Every override logged with rationale

---

### Task 13: Integration Tests for Full Mutation Cycle
**Source**: BUILD_PRIORITY_ROADMAP.md (lines 553-622)  
**Priority**: MEDIUM  
**Time**: 3 days  
**Dependencies**: All Phase 1-3 tasks  
**Status**: [x] Complete

**New File**: `tests/test_mutation_end_to_end.py`

**Test Scenarios**:
1. `test_full_mutation_cycle()`: Propose ? Vote ? Test ? Promote
2. `test_rollback_after_regression()`: Detect ? Assess ? Approve ? Rollback

---

## Additional Requirements

### Task 14: Implement 5 MLLM Decision Categories
**Source**: MLLM_CURATION_STRATEGY.md (lines 14-330)  
**Priority**: MEDIUM  
**Time**: 5-7 days  
**Dependencies**: Task 7  
**Status**: [x] Complete

**Categories**:
1. **Mutation Mission Alignment Check** (Alpha proposes)
   - Model: Qwen2.5-7B
   - Output: alignment_vote, confidence, reasoning

2. **Test Result Analysis** (Beta evaluates)
   - Model: DeepSeek-Coder-6.7B
   - Output: pass_rate, critical_failures, recommendation

3. **Security & Prompt Injection Detection** (Autobot cross-checks)
   - Model: Phi-4-Mini
   - Output: injection_detected, overall_risk, confidence

4. **Decision Logging & Reasoning Snapshot** (Autobot records)
   - Method: Structured JSON (no model)
   - Output: Deterministic audit record

5. **Rollback Safety Assessment** (Autobot, requires approval)
   - Model: Qwen2.5-14B
   - Output: rollback_safe, data_loss_risk, fields_lost

---

### Task 15: Build Model Metrics Collector
**Source**: MLLM_CURATION_STRATEGY.md (lines 431-464)  
**Priority**: LOW  
**Time**: 1-2 days  
**Dependencies**: Task 7  
**Status**: [x] Complete

**New File**: `instrumentation/model_metrics.py`

**Requirements**:
- Log every model invocation (tokens, latency, accuracy)
- Alert if accuracy <75%
- Track model performance over time
- Enable model swapping based on metrics

---

### Task 16: Build Archival Policy System
**Source**: OVERRIDE_APPROVAL_ESCALATION.md (lines 350-413)  
**Priority**: LOW  
**Time**: 1-2 days  
**Dependencies**: Task 10  
**Status**: [x] Complete

**New File**: `storage/archival_policy.py`

**Requirements**:
- Config-driven archival policies
- Daily archival job (cron/scheduler)
- Archive to S3/Glacier based on category
- Log all archival actions

---

## Implementation Priority Summary

### CRITICAL (Today)
- [ ] Task 1: Fix consensus voting to unanimous
- [ ] Task 2: Expand AgentState schema

### HIGH (This Week - Days 1-7)
- [ ] Task 3: Refactor agents to vote
- [ ] Task 4: Build version store
- [ ] Task 5: Build decision logger
- [ ] Task 6: Build operator interface

### MEDIUM (Next 2 Weeks - Days 8-21)
- [ ] Task 7: Build MLLM registry
- [ ] Task 8: Build rollback engine
- [ ] Task 9: Build unified notifier
- [ ] Task 10: Build storage tracker
- [ ] Task 11: Build escalation handler
- [ ] Task 12: Write unit tests
- [ ] Task 13: Write integration tests
- [ ] Task 14: Implement 5 MLLM categories

### LOW (Week 4+ - Days 22+)
- [ ] Task 15: Build model metrics collector
- [ ] Task 16: Build archival policy system

---

## Questions for Operator (Martin)

**Source**: IMMEDIATE_ACTION_PLAN.md (lines 472-478), AUTONOMOUSAGENT_QA_AUDIT.md (lines 450-456)

1. **Voting timeout**: If council hasn't voted in 30 min, auto-escalate or wait forever?
2. **Operator timeout**: If you don't respond to Telegram in 1 hour, auto-reject or hold?
3. **Rollback authority**: Council vote required, or just your Telegram approval?
4. **Storage budget**: How much disk for logs + versions? (Assume 500GB?)
5. **Unanimous voting tiebreaker**: If council deadlocks, auto-escalate or timeout?
6. **Model specialization**: Should each agent use different models, or same for all?

---

## Success Criteria

| Milestone | Target Date | Status |
|-----------|-------------|--------|
| Fix consensus voting | TODAY | ? Pending |
| Expand state schema | TODAY | ? Pending |
| Agents vote + log | Day 5 | ? Pending |
| Version store | Day 7 | ? Pending |
| Decision logger | Day 8 | ? Pending |
| Operator interface | Day 10 | ? Pending |
| MLLM registry | Day 14 | ? Pending |
| Rollback engine | Day 16 | ? Pending |
| Storage tracker | Day 21 | ? Pending |
| Unit tests | Day 24 | ? Pending |
| Integration tests | Day 27 | ? Pending |

---

**Plan Generated**: July 25, 2026  
**Next Action**: Begin EMERGENCY FIXES (consensus voting + state schema)  
**Estimated Total Time**: 28 days (4 weeks)
