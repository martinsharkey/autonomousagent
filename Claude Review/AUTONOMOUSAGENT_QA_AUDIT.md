# QA Audit: autonomousagent Repository

**Auditor**: Claude  
**Date**: July 25, 2026  
**Repository**: github.com/martinsharkey/autonomousagent  
**Current Stage**: Early alpha (4 commits, basic orchestration working)

---

## Executive Summary

The repo has a **solid foundation** with LangGraph orchestration, three-agent architecture, and governance layers. However, it diverges from your Superior Trio council model in critical ways:

| Requirement | Status | Issue |
|-------------|--------|-------|
| **Unanimous voting** | ❌ WRONG | Uses 2/3 majority (line 36 in consensus.py) |
| **Operator override via Telegram** | ❌ MISSING | No integration, no escalation path |
| **Code versioning + rollback** | ⚠️ PARTIAL | Hashes exist, but no version storage or rollback logic |
| **Immutable audit log** | ✅ GOOD | HMAC-chained, fsync enforced, integrity check present |
| **Semantic cache** | ✅ GOOD | Prevent duplicate invocations implemented |
| **TTL circuit breaker** | ✅ GOOD | Loop count limit = 5 enforced in routing |
| **MLLM specialization** | ⚠️ PARTIAL | Models hardcoded, no registry or swapping |
| **Storage tracking** | ❌ MISSING | No inventory, no archival planning |
| **State schema immutability** | ⚠️ NEEDS WORK | TypedDict basic, missing operator override fields |

---

## What's Working Well ✅

### 1. **Audit Log (Zero-Trust Protocol)**

**File**: `governance/audit_log.py`

✅ **Strengths**:
- Append-only log with fsync (data durability)
- HMAC-SHA256 chaining (tamper detection)
- Previous entry hash linking (immutability verification)
- `verify_log_integrity()` validates chain on read

✅ **Code Quality**:
```python
# Append-only: no UPDATE/DELETE operations
with open(log_file, "a") as f:
    f.write(json.dumps(log_entry) + "\n")
    f.flush()
    os.fsync(f.fileno())  # Force disk write
```

**Verdict**: Production-ready for audit trail. This is your L4 governance layer (immutable log).

---

### 2. **TTL Circuit Breaker**

**File**: `core/graph.py` (lines 14-16)

✅ **Strengths**:
- Hard limit at `loop_count >= 5`
- Deterministic (no LLM involved)
- Blocks any further routing after TTL breach

```python
if state["loop_count"] >= 5:
    print(f"[SYSTEM OVERRIDE] TTL limit {state['loop_count']} breached. Terminating.")
    return "terminal_fallback"
```

**Verdict**: Correctly implements loop prevention.

---

### 3. **Semantic Cache (Duplicate Prevention)**

**File**: `core/semantic_cache.py` (referenced but not shown)

✅ **Pattern**:
```python
def autobot_with_cache(state: AgentState):
    duplicate = check_duplicate_invocation(state)
    if duplicate:
        return {
            "messages": [{...,"SYSTEM OVERRIDE: YOU HAVE ALREADY TRIED THIS ACTION..."}]
        }
    result = autobot_node(state)
    result["loop_count"] = state["loop_count"] + 1
    return result
```

**Verdict**: Prevents tool call replays. Good pattern.

---

## What's Broken/Wrong ❌

### 1. **CRITICAL: Voting Consensus is NOT Unanimous**

**File**: `governance/consensus.py` (lines 34-39)

```python
def check_consensus(self, proposal_id: str) -> str:
    votes = self.votes[proposal_id]
    approvals = sum(1 for v in votes.values() if v == "approve")
    
    if approvals >= len(self.agents) * 2 / 3:  # ❌ 2/3 MAJORITY, NOT UNANIMOUS
        return "approved"
    else:
        return "rejected"
```

**Problem**: You specified **unanimous consent** (all 3 must approve). This code uses 2/3 majority.

**Fix Required**:
```python
def check_consensus(self, proposal_id: str) -> str:
    votes = self.votes[proposal_id]
    
    if len(votes) < len(self.agents):
        return "pending"
    
    # Unanimous: ALL must approve
    if all(v == "approve" for v in votes.values()):
        self.proposals[proposal_id]["status"] = "approved"
        return "approved"
    else:
        self.proposals[proposal_id]["status"] = "rejected"
        return "rejected"
```

**Action**: Tell Bob to change line 36 from `>= 2/3` to `== all`.

---

### 2. **CRITICAL: No Operator Override Capability**

**Missing**: No Telegram integration, no escalation path to you.

**What exists**:
- `core/telegram.py` referenced in `main.py`, but sends notifications only (no buttons/interaction)
- No method to override council votes
- No rollback approval flow

**What needs to be added**:
- Telegram bot with inline buttons (APPROVE/HOLD/REJECT)
- Callback handler that routes override decisions to Autobot
- State field: `operator_override` and `operator_rationale`
- Logging: `log_decision("OPERATOR_OVERRIDE_PROMOTE", ...)`

**Files to create**:
```python
# core/operator_interface.py
class OperatorInterface:
    async def request_council_decision(self, mutation_id: str, votes: Dict[str, bool]):
        # Send to Telegram with buttons
        # Wait for Martin's response
        # Return override decision
        pass

# governance/telegram_handler.py
async def button_callback(query):
    # Handle APPROVE/HOLD/REJECT buttons
    # Log operator decision
    # Notify Autobot of override
```

**Timeline to fix**: Bob adds this in Phase 2 (per BUILD_PRIORITY_ROADMAP.md).

---

### 3. **WRONG: State Schema Missing Operator Fields**

**File**: `core/state.py`

Current:
```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    loop_count: int
    recent_tool_invocations: Annotated[list[str], operator.add]
    completed_nodes: Annotated[list[str], operator.add]
    codebase_hash: str
```

**Missing**:
```python
    # Voting state
    active_mutation_id: Optional[str]
    council_votes: Dict[str, bool]  # {"autobot": True, "alpha": True, "beta": True}
    mission_alignment_rationale: Optional[str]
    
    # Operator override
    operator_override: Optional[str]  # "APPROVE", "HOLD", "REJECT"
    operator_override_rationale: Optional[str]
    
    # Escalation
    escalation_reason: Optional[str]
    requires_operator_approval: bool
    
    # Versioning
    proposed_version: Optional[str]
    current_version: str
    rollback_pending: bool
    rollback_approved: bool
```

**Action**: Expand `AgentState` TypedDict before Phase 1 is complete.

---

### 4. **MISSING: Code Versioning & Rollback**

**Status**: Not in repo.

**What's needed**:
- `core/version_store.py` — immutable version repository (SHA256 hashes, parent lineage)
- `core/rollback.py` — restore code + state from version X
- Version manifest (JSON or SQLite)

**Example from AUTONOMOUSAGENT_BUILD_PRIORITY_ROADMAP.md**:
```python
class VersionStore:
    def save_version(self, code: str, member_id: str, mutation_id: str, parent_version: str = None) -> str:
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:12]
        version_id = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}_{code_hash}"
        # Save code + metadata
        return version_id
    
    def get_version(self, version_id: str) -> str:
        # Retrieve code from immutable storage
        pass
```

**Timeline**: Phase 1.2 in BUILD_PRIORITY_ROADMAP (Bob's responsibility).

---

### 5. **PARTIAL: MLLM Models Hardcoded**

**File**: `agents/autobot.py` (lines 7-8)

```python
MODEL_NAME = os.getenv("AUTOBOT_MODEL", "qwen3.5:4b")
FALLBACK_MODEL = os.getenv("AUTOBOT_FALLBACK_MODEL", "llama3.2:1b")
```

**Issue**: Model names buried in agent files. No registry, no dynamic swapping.

**What's needed** (per MLLM_CURATION_STRATEGY.md):
```python
# models/mllm_registry.py
MLLM_REGISTRY = {
    "voting_evaluator": {
        "model": "Qwen2.5-7B",
        "context_size": 32K,
        "memory_footprint": "3.8 GB",
        "specialized_for": "mission alignment voting"
    },
    "test_analyzer": {
        "model": "DeepSeek-Coder-6.7B",
        "context_size": 4K,
        "memory_footprint": "3.6 GB",
        "specialized_for": "test result analysis"
    },
    # ... others
}

class MLLMLoader:
    def load_model(self, model_name: str, force: bool = False):
        # LRU eviction if budget exceeded
        # Sequential loading to stay under 8GB
```

**Action**: Bob builds this in Phase 2.1.

---

### 6. **MISSING: Storage Tracking**

**Status**: Not in repo.

**What needs to exist**:
```python
# storage/storage_tracker.py
class StorageTracker:
    def log_write(self, path: str, size_bytes: int, category: str, retainable: bool = True):
        # Track every write
        # Calculate usage %
        # Alert at 80%
        pass
    
    def suggest_archival_candidates(self) -> List[str]:
        # Return paths eligible for archival
        pass

# Typical categories:
# - decision_log (hot 90 days, archive S3, delete 1 year)
# - test_output (hot 14 days, archive S3, delete 90 days)
# - code_version (hot forever, archive glacier)
```

**Action**: Bob builds this in Phase 3.

---

### 7. **PARTIAL: Agent Implementations Too Generic**

**File**: `agents/autobot.py` (lines 31-36)

```python
def autobot_node(state: AgentState):
    print(f"\n--- [AUTOBOT] Analyzing State (Loop: {state['loop_count']}) ---")
    response = autobot_llm.invoke(state["messages"])
    return {
        "messages": [response],
        "completed_nodes": ["autobot"]
    }
```

**Issue**: Nodes are generic wrappers. No voting logic, no consensus checking, no mutation proposals.

**What they should do**:
- **Autobot** (orchestrator): Proposes mutations, casts deciding vote on security
- **Alpha** (evaluator): Votes on mission alignment + test readiness
- **Beta** (worker): Votes on feasibility, reports test results

**Action**: Refactor agents to include voting state updates + decision logging (Phase 1.4 onwards).

---

## What's Missing Entirely ❌

| Component | Location | Priority | Effort |
|-----------|----------|----------|--------|
| Operator override + Telegram integration | `core/operator_interface.py` | CRITICAL | 2-3 days |
| Code versioning + rollback | `core/version_store.py` | CRITICAL | 3-5 days |
| MLLM registry + loader | `models/mllm_registry.py` | HIGH | 2-3 days |
| Storage tracking + archival | `storage/storage_tracker.py` | HIGH | 2-3 days |
| Voting state in agents | `agents/*.py` refactor | CRITICAL | 3-5 days |
| Rollback safety assessment | `governance/rollback_judge.py` | HIGH | 1-2 days |
| Unified interface (chat + Telegram sync) | `interfaces/unified_notifier.py` | MEDIUM | 2-3 days |

---

## Recommendations (Priority Order)

### **Immediate (Before Next Commit)**

1. ✅ **Fix consensus voting**: Change 2/3 to unanimous (1 line change, massive impact)
2. ✅ **Expand state schema**: Add voting, override, versioning fields to `AgentState`
3. ✅ **Refactor agents**: Make them actually vote + log decisions (not just invoke LLM)

### **Phase 1 (This Week)**

4. Build version store (immutable repository)
5. Build rollback engine
6. Build operator interface + Telegram integration
7. Write unit tests for voting + rollback

### **Phase 2 (Next Week)**

8. MLLM registry + loader
9. Unified interface (chat + Telegram sync)
10. Integration tests (end-to-end mutation cycles)

### **Phase 3 (Week After)**

11. Storage tracker + archival planning
12. Monitoring + observability

---

## Code Quality Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Audit logging** | A | HMAC chaining, fsync, integrity checks—excellent |
| **State management** | B- | TypedDict is good, but needs more fields for voting/override |
| **Consensus logic** | F | Uses majority instead of unanimous—fix immediately |
| **Error handling** | C+ | Fallback models exist, but no rollback on failure |
| **Testing** | D | 4 commits, probably minimal tests—need 100% coverage for governance |
| **Documentation** | B+ | README is clear, but internal code needs docstrings |
| **Security** | B | Sandbox references, but no actual implementation yet |

---

## Audit Checklist (For Martin's Code Review)

- [ ] **Consensus voting unanimous?** → NO, fix to: `all(v == "approve" for v in votes.values())`
- [ ] **State schema has voting fields?** → NO, add: `operator_override`, `council_votes`, etc.
- [ ] **Operator override integrated?** → NO, needed for Telegram interaction
- [ ] **Version store immutable?** → NO, must build
- [ ] **Audit log tamper-proof?** → YES, HMAC chaining works
- [ ] **TTL circuit breaker safe?** → YES, hard limit at 5
- [ ] **Semantic cache prevents replays?** → YES, pattern is sound
- [ ] **MLLM swappable?** → NO, models hardcoded
- [ ] **Storage tracked?** → NO, needed for archival planning
- [ ] **All decisions logged?** → PARTIAL, voting not yet logged

---

## Next Steps for Bob

1. **Fix consensus voting** (emergency):
   ```python
   # Change in governance/consensus.py line 36
   if all(v == "approve" for v in votes.values()):
   ```

2. **Expand state schema**:
   ```python
   # Update core/state.py with voting + override fields
   ```

3. **Refactor agents to vote**:
   - Each agent evaluates proposal using MLLM
   - Calls `consensus.cast_vote()`
   - Logs decision

4. **Build version store** (new file):
   - Immutable code repository
   - Parent lineage tracking
   - Rollback capability

5. **Add operator interface** (new file):
   - Telegram bot handler
   - Button callbacks
   - Override decision routing

---

## Next Steps for Martin (Audit)

1. Review Bob's consensus.py fix (1 line change, approve/reject)
2. Audit expanded state schema (no silent mutations allowed)
3. Review agent refactoring (voting logic + decision logging)
4. Verify version store immutability (can't overwrite, can't delete)
5. Test operator override flow end-to-end (Telegram button → Autobot decision)

---

## Files to Review (in order)

1. `governance/consensus.py` — Fix unanimous voting ⚠️
2. `core/state.py` — Expand schema ⚠️
3. `agents/autobot.py`, `alpha_evaluator.py`, `beta_worker.py` — Add voting ⚠️
4. `governance/audit_log.py` — Already good ✅
5. `core/graph.py` — TTL circuit breaker, routing ✅

---

## Questions for Martin

1. **Unanimous voting tiebreaker**: If council deadlocks (not all respond in time), does it auto-escalate to you, or do you have a timeout?
2. **Rollback authority**: Should rollback require council vote, or just your Telegram approval?
3. **Model specialization**: Should each agent use different models (voting vs. code generation), or same model for all three?
4. **Storage budget**: How much disk space for logs + versions? (Estimate: ~500GB?)

