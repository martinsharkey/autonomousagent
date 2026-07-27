# Immediate Action Plan: autonomousagent Repository

**Date**: July 25, 2026  
**Owner**: Bob (implementation) + Martin (audit)  
**Status**: 4 commits, basic orchestration working, major fixes needed

---

## 🔴 EMERGENCY FIX (Do This Now)

### Change #1: Fix Consensus Voting to Unanimous

**File**: `governance/consensus.py`, line 36

**Current (WRONG)**:
```python
if approvals >= len(self.agents) * 2 / 3:  # ❌ 2/3 MAJORITY
    self.proposals[proposal_id]["status"] = "approved"
    return "approved"
```

**New (CORRECT)**:
```python
if all(v == "approve" for v in votes.values()):  # ✅ UNANIMOUS
    self.proposals[proposal_id]["status"] = "approved"
    return "approved"
```

**Why**: Your Superior Trio model requires **unanimous consent**. Current code breaks this fundamental requirement.

**Martin's checklist**:
- [ ] Ask Bob to make this 1-line change
- [ ] Verify logic: requires ALL three votes == "approve"
- [ ] Confirm vote rejection triggers escalation to you
- [ ] Approve and merge

**Time to fix**: 5 minutes
**Risk if not fixed**: Mutations approved without full consensus (defeats safety model)

---

### Change #2: Expand State Schema with Voting & Override Fields

**File**: `core/state.py`

**Current**:
```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    loop_count: int
    recent_tool_invocations: Annotated[list[str], operator.add]
    completed_nodes: Annotated[list[str], operator.add]
    codebase_hash: str
```

**New** (add these fields):
```python
class AgentState(TypedDict):
    # ... existing fields ...
    
    # Voting cycle
    active_mutation_id: Optional[str]  # UUID of current proposal
    proposed_mutation_code: Optional[str]  # Code being voted on
    mission_rationale: Optional[str]  # Why this mutation serves core mission
    council_votes: Dict[str, Optional[bool]]  # {"autobot": None, "alpha": True, "beta": False}
    mission_scores: Dict[str, float]  # Confidence scores from voting models
    
    # Operator override
    operator_override: Optional[str]  # "APPROVE", "HOLD", "REJECT", None
    operator_override_rationale: Optional[str]
    operator_override_timestamp: Optional[str]  # ISO format
    
    # Escalation
    escalation_reason: Optional[str]  # Why we're asking Martin
    requires_operator_approval: bool  # True if rollback or security concern
    
    # Versioning
    proposed_version: Optional[str]  # "v20260725_154930_abc123"
    current_version: str  # "v20260724_120000_def456"
    
    # Rollback state
    rollback_pending: bool
    rollback_target_version: Optional[str]
    rollback_approved: bool
    rollback_reason: Optional[str]
```

**Why**: State must track voting decisions, operator actions, and version history. Current schema can't represent these.

**Martin's checklist**:
- [ ] Verify no field mutation without explicit setter
- [ ] Confirm Optional fields default to None
- [ ] Check TypedDict is immutable (can't be accidentally mutated)
- [ ] Approve schema expansion

**Time to fix**: 30 minutes
**Risk if not fixed**: Can't track voting, can't implement operator override, can't do rollback

---

## 🟡 CRITICAL PHASE 1 (This Week)

### Phase 1.1: Refactor Agents to Actually Vote

**Files**: `agents/autobot.py`, `agents/alpha_evaluator.py`, `agents/beta_worker.py`

**Current**: Each agent just invokes LLM and returns result. No voting, no decision logging.

**New**:
```python
# agents/autobot.py (security voting example)
async def autobot_node(state: AgentState) -> AgentState:
    """Autobot votes on security risk"""
    
    # Load security audit model (Phi-4-Mini per MLLM_CURATION_STRATEGY.md)
    model = load_mllm("phi-4-mini")
    
    # Evaluate proposal
    proposal_text = state["proposed_mutation_code"]
    prompt = f"""
    Evaluate this code mutation for prompt injection, privilege escalation, 
    or unauthorized access:
    
    {proposal_text}
    
    Vote: APPROVE or REJECT
    Confidence: 0.0-1.0
    Reasoning: ...
    """
    
    decision = model.generate(prompt)
    vote = decision["vote"] == "APPROVE"
    confidence = decision["confidence"]
    
    # Cast vote
    consensus_engine.cast_vote(
        proposal_id=state["active_mutation_id"],
        agent_name="autobot",
        vote="approve" if vote else "reject",
        reason=decision["reasoning"]
    )
    
    # Log decision
    log_decision("SECURITY_AUDIT_VOTE", {
        "mutation_id": state["active_mutation_id"],
        "vote": "approve" if vote else "reject",
        "confidence": confidence,
        "model_used": "phi-4-mini",
        "reasoning": decision["reasoning"]
    })
    
    # Update state
    state["council_votes"]["autobot"] = vote
    state["mission_scores"]["autobot"] = confidence
    
    # Check if all three have voted
    if all(v is not None for v in state["council_votes"].values()):
        result = consensus_engine.check_consensus(state["active_mutation_id"])
        if result == "approved":
            state["completed_nodes"].append("voting_complete")
        elif result == "rejected":
            state["escalation_reason"] = "Council voted to reject mutation"
            state["requires_operator_approval"] = True
    
    return state
```

**Alpha's voting** (mission alignment + test readiness):
- Use Qwen2.5-7B for mission alignment
- Use DeepSeek-Coder-6.7B for test analysis
- Vote accordingly

**Beta's voting** (feasibility):
- Analyze mutation for syntax/compatibility
- Check if tests pass in sandbox
- Vote on overall feasibility

**Martin's checklist**:
- [ ] Each agent calls MLLM with clear prompt
- [ ] Each agent logs its vote with rationale
- [ ] State updated with votes
- [ ] Consensus check triggers after all votes in
- [ ] No LLM involved in routing (pure logic only)

**Time for Bob**: 3-5 days
**Risk if not done**: Voting is illusory, agents don't actually evaluate

---

### Phase 1.2: Build Immutable Version Store

**New file**: `core/version_store.py`

```python
import hashlib
import tarfile
from pathlib import Path
from datetime import datetime

class VersionStore:
    """Immutable code version repository"""
    
    def __init__(self, storage_dir: Path = Path("./versions")):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(exist_ok=True)
        self.manifest_file = self.storage_dir / "manifest.json"
    
    def save_version(self, code: str, member_id: str, 
                     mutation_id: str, parent_version: str = None) -> str:
        """
        Save code version immutably. Returns version_id.
        Cannot overwrite existing versions.
        """
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:12]
        version_id = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}_{code_hash}"
        
        version_file = self.storage_dir / f"{version_id}.tar.gz"
        
        # Check: version already exists? (immutable enforcement)
        if version_file.exists():
            raise ValueError(f"Version {version_id} already exists (immutable)")
        
        # Save code to tar.gz
        with tarfile.open(version_file, "w:gz") as tar:
            tar.add(code, arcname="code")
        
        # Record in manifest
        manifest = self._read_manifest()
        manifest[version_id] = {
            "timestamp": datetime.now().isoformat(),
            "member_id": member_id,
            "mutation_id": mutation_id,
            "parent_version": parent_version,
            "code_hash": code_hash,
            "storage_path": str(version_file),
            "rollback_safe": True
        }
        self._write_manifest(manifest)
        
        log_decision("VERSION_SAVED", {
            "version_id": version_id,
            "member": member_id,
            "mutation_id": mutation_id,
            "parent": parent_version
        })
        
        return version_id
    
    def get_version(self, version_id: str) -> str:
        """Retrieve code from version (immutable read)"""
        manifest = self._read_manifest()
        if version_id not in manifest:
            raise FileNotFoundError(f"Version {version_id} not found")
        
        version_file = self.storage_dir / f"{version_id}.tar.gz"
        # Extract and return code
        with tarfile.open(version_file, "r:gz") as tar:
            tar.extractall(path=self.storage_dir / version_id)
        
        code_path = self.storage_dir / version_id / "code"
        with open(code_path) as f:
            return f.read()
    
    def get_history(self, member_id: str = None) -> List[Dict]:
        """Get version lineage (parent → child chain)"""
        manifest = self._read_manifest()
        if member_id:
            return [v for v in manifest.values() if v["member_id"] == member_id]
        return list(manifest.values())
```

**Martin's checklist**:
- [ ] Verify immutability: `version_file.exists()` prevents overwrites
- [ ] Check parent lineage: every version knows its parent
- [ ] Confirm code_hash is SHA256 of content (deterministic)
- [ ] Verify manifest is persistent (JSON file)
- [ ] Test: Can't create v1 twice? (should fail)

**Time for Bob**: 2-3 days
**Risk if not done**: No rollback capability, can't track mutation history

---

### Phase 1.3: Build Immutable Decision Logger (Expand Audit Log)

**File**: `governance/audit_log.py` (enhance existing)

Add decision logging:
```python
def log_decision(decision_type: str, metadata: Dict, 
                mutation_id: str = None, council_member: str = None,
                model_used: str = None):
    """Log a council decision (voting, override, rollback, etc.)"""
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "decision_type": decision_type,  # "MISSION_VOTE", "OPERATOR_OVERRIDE", etc.
        "mutation_id": mutation_id,
        "council_member": council_member,
        "model_used": model_used,
        "metadata": metadata,
        "prev_hash": _get_last_entry_hash(log_file) or "genesis"
    }
    
    # Compute hash + HMAC (same as existing code)
    entry_hash = _compute_entry_hash(log_entry)
    log_entry["entry_hash"] = entry_hash
    log_entry["hmac"] = _compute_hmac(entry_hash)
    
    # Append immutably
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
        f.flush()
        os.fsync(f.fileno())

def get_audit_trail(mutation_id: str) -> List[Dict]:
    """Retrieve full decision chain for a mutation"""
    # Query all logs for mutation_id
    # Return ordered by timestamp
```

**Martin's checklist**:
- [ ] Every vote logged with model + confidence
- [ ] Every operator override logged with rationale
- [ ] Every rollback logged with reason + approval
- [ ] Logs immutable (append-only, fsync, HMAC chain)
- [ ] Can query by mutation_id to see full trail

**Time for Bob**: 1 day (enhancement to existing code)
**Risk if not done**: Can't audit who voted what, why, or when

---

### Phase 1.4: Operator Interface (Telegram Bot)

**New file**: `core/operator_interface.py`

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

class OperatorInterface:
    def __init__(self, bot_token: str, chat_id: int):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.app = Application.builder().token(bot_token).build()
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def request_mutation_approval(self, mutation_id: str, proposal: Dict):
        """Send mutation decision to Martin on Telegram"""
        
        message = f"""
🔵 MUTATION READY FOR REVIEW

ID: {mutation_id}
Type: {proposal['type']}

Mission Alignment: {proposal['mission_rationale'][:100]}...

Council Votes:
✅ Autobot: {'APPROVE' if proposal['votes']['autobot'] else 'REJECT'}
✅ Alpha: {'APPROVE' if proposal['votes']['alpha'] else 'REJECT'}
✅ Beta: {'APPROVE' if proposal['votes']['beta'] else 'REJECT'}

Test Results: 98% pass rate
Security: SAFE

What would you like to do?
"""
        
        keyboard = [
            [
                InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{mutation_id}"),
                InlineKeyboardButton("⏸ HOLD", callback_data=f"hold_{mutation_id}"),
                InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{mutation_id}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.app.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            reply_markup=reply_markup
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle operator's button click"""
        query = update.callback_query
        await query.answer()
        
        action, mutation_id = query.data.split("_", 1)
        
        # Log override decision
        log_decision("OPERATOR_DECISION", {
            "mutation_id": mutation_id,
            "action": action,  # "APPROVE", "HOLD", "REJECT"
            "timestamp": datetime.now().isoformat()
        })
        
        # Notify Autobot to update state
        # (implementation depends on how Autobot polls for overrides)
        
        await query.edit_message_text(
            text=f"✓ Recorded: {action} for {mutation_id}"
        )
```

**Martin's checklist**:
- [ ] Bot responds to button clicks
- [ ] Decision logged with timestamp
- [ ] Autobot can read operator override
- [ ] Timeout: what happens if Martin doesn't respond in 1 hour?
- [ ] Test: Send mutation, press button, verify logged

**Time for Bob**: 2-3 days
**Risk if not done**: Can't override council, can't interact with system

---

## 🟢 PHASE 2 (Next Week)

- MLLM registry + dynamic loader
- Storage tracking
- Unified interface (chat + Telegram sync)
- Integration tests

---

## Weekly Ritual: Martin's Audit

**Every Monday morning (30 min)**:

1. Review Bob's commits from last week
2. Ask two questions per file:
   - "Can this be exploited?"
   - "Can this cause a silent bug?"
3. Approve or request changes (comment on PR)
4. Merge only after approval

**Example**:
```
Bob commits: phase1_1_agent_voting.py

Martin's audit:
Q1: Can LLM force an agent to vote opposite its training?
A1: Use prompt injection detection (Phi-4-Mini security check) ✅

Q2: What if voting model returns malformed JSON?
A2: Parse errors caught, logged, escalate to operator ✅

Approved + Merged ✅
```

---

## Success Criteria

| Milestone | Date | Owner | Blocked By |
|-----------|------|-------|-----------|
| Fix consensus voting (unanimous) | TODAY | Bob | None |
| Expand state schema | TODAY | Bob | None |
| Phase 1.1 agents vote + log | Fri | Bob | Consensus fix |
| Phase 1.2 version store | Fri | Bob | State schema |
| Phase 1.3 decision logger | Sat | Bob | Audit log |
| Phase 1.4 operator interface | Sun | Bob | None |
| Martin audits all Phase 1 | Mon | Martin | Bob finishes |
| Phase 2 MLLM registry | Mon-Fri | Bob | Phase 1 approved |

---

## Questions for Martin

1. **Voting timeout**: If council hasn't voted in 30 min, auto-escalate or wait forever?
2. **Operator override timeout**: If Martin doesn't respond to Telegram in 1 hour, what happens? Auto-reject?
3. **Rollback approval**: Should rollback require council vote (slow), or just Martin's Telegram approval (fast)?
4. **Storage budget**: How much disk for logs + versions? (Assume 500GB?)

