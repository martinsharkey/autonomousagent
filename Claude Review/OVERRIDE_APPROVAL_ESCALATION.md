# Operator Override, Approval & Escalation Framework

## Overview
Martin (operator) has three intervention points:
1. **Override council decision** (mutation approved/rejected → Martin says no/yes)
2. **Approve/reject rollback** (Autobot proposes rollback → Martin authorizes)
3. **Escalation communication** (council deadlocked or security alert → pings Martin)

All interventions must:
- Be logged with full context
- Include rationale (why Martin overrode)
- Be auditable post-hoc
- Work via **both Telegram and VS Code chat** (dual interface)

---

## Tier 1: Council Decision Override

### Scenario 1A: Council says "APPROVED" but Martin disagrees

```
Council votes: YES, YES, YES (unanimous)
Mutation status: READY TO PROMOTE
↓
[Autobot initiates promotion]
↓
[Martin gets notification on Telegram + Chat]
"🟢 MUTATION APPROVED by council
 Proposal ID: mut-2024-001
 Type: Core encryption upgrade
 Mission alignment: ✓ (Qwen2.5-7B)
 Tests pass rate: 98% (DeepSeek-6.7B)
 Security: SAFE (Phi-4-Mini)

 Action in: [ APPROVE ] [ HOLD ] [ REJECT OVERRIDE ]"
↓
Martin: "HOLD"  ← Pauses promotion
↓
[Council notified of hold]
Autobot: "Operator placed hold on mut-2024-001. 
 Awaiting rationale..."
↓
Martin provides rationale via chat:
"I'm concerned this touches the payment API layer.
 Run additional integration tests before promotion."
↓
[Decision logged]
log_decision("OVERRIDE_HOLD", {
    "mutation_id": "mut-2024-001",
    "initiated_by": "Martin",
    "override_type": "HOLD_BEFORE_PROMOTION",
    "rationale": "Payment API layer concerns; need integration tests",
    "council_votes": {"Autobot": True, "CloneAlpha": True, "CloneBeta": True},
    "timestamp": datetime.now(),
    "storage_location": "logs/override/mut-2024-001.json"
})
↓
Council re-evaluates: Run additional tests, then vote again.
If still YES: Martin can APPROVE or OVERRIDE_REJECT (veto)
```

### Scenario 1B: Council says "REJECTED" but Martin thinks it's sound

```
Council votes: YES, YES, NO (CloneBeta dissents)
Mutation status: REJECTED (unanimous consent rule)
↓
[Autobot notifies: mutation rejected]
↓
Martin on Telegram:
"I believe CloneBeta is overly cautious here.
 Override to promote: mut-2024-001"
↓
[Decision logged]
log_decision("OVERRIDE_PROMOTE", {
    "mutation_id": "mut-2024-001",
    "initiated_by": "Martin",
    "override_type": "PROMOTE_DESPITE_DISSENT",
    "operator_rationale": "CloneBeta overly cautious; mutation is sound",
    "council_votes": {"Autobot": True, "CloneAlpha": True, "CloneBeta": False},
    "override_confidence": "high",  # Martin provided clear reasoning
    "timestamp": datetime.now()
})
↓
Autobot: "Override confirmed. Promoting mut-2024-001.
 Logged as OPERATOR_OVERRIDE_PROMOTE.
 Future audits will flag this decision."
↓
Mutation proceeds to testing + promotion
```

### Scenario 1C: Council deadlocked (unclear consensus)

```
Voting incomplete after 30 minutes:
- Autobot: YES
- CloneAlpha: UNCERTAIN (test results ambiguous)
- CloneBeta: waiting for more data

Status: DEADLOCK
↓
[Autobot escalates to Martin on Telegram]
"⚠️ VOTING DEADLOCK

Mutation: mut-2024-002
Time deadlocked: 30 min
CloneAlpha vote: UNCERTAIN
  Reason: Test coverage increased but latency +15%
  
What should I do?
[ REQUEST MORE TIME ] [ ESCALATE TO VOTING MODEL AGAIN ] [ MANUAL REVIEW NEEDED ]"
↓
Martin: "REQUEST MORE TIME (add 15 minutes)"
↓
[Logged]
log_decision("DEADLOCK_ESCALATION", {
    "mutation_id": "mut-2024-002",
    "deadlock_duration_min": 30,
    "council_status": {"Autobot": "YES", "CloneAlpha": "UNCERTAIN", "CloneBeta": "WAITING"},
    "operator_decision": "REQUEST_MORE_TIME",
    "extra_time_granted_min": 15,
    "timestamp": datetime.now()
})
↓
After 15 minutes: CloneBeta provides additional analysis
CloneAlpha re-votes: YES
Consensus reached.
```

---

## Tier 2: Rollback Override (Requires Escalation to Martin)

**Policy**: Rollback always needs Martin's explicit approval (not council vote).

### Scenario 2A: Autobot proposes rollback (mutation caused regression)

```
CloneAlpha_v2 promoted 2 hours ago
↓
Autobot detects: "Error rate increased 300% post-promotion"
↓
Autobot: "REGRESSION DETECTED. Initiating rollback assessment..."
↓
[Phi-4-Mini] Rollback safety check runs
Output: "Rollback to v1.2.5 is SAFE"
↓
[Escalation to Martin on Telegram]
"🔴 REGRESSION ALERT

Current version: v1.2.5 (promoted 2h ago)
Error rate: 0.1% → 3% (300% increase)

Rollback assessment: SAFE
Target version: v1.2.4 (last known good)
Data loss risk: NONE

Approve rollback?
[ YES - ROLLBACK NOW ] [ HOLD ] [ INVESTIGATE FIRST ]"
↓
Martin: "YES - ROLLBACK NOW"
↓
[Decision logged - CRITICAL]
log_decision("ROLLBACK_APPROVED", {
    "initiated_by": "Autobot",
    "regression_detected": True,
    "metric": "error_rate",
    "degradation": 0.001 → 0.03,
    "approved_by": "Martin",
    "approval_rationale": None,  # Autobot auto-escalated
    "target_version": "v1.2.4",
    "rollback_safety": "SAFE",
    "timestamp": datetime.now(),
    "approval_timestamp": datetime.now() + timedelta(minutes=2),
    "storage_location": "logs/rollback/v1.2.5-rollback.json"
})
↓
Autobot executes rollback:
1. Restore code from v1.2.4 hash
2. Restore state snapshot from v1.2.4
3. Verify all three council members boot successfully
4. Resume operations
↓
[Autobot notifies Martin on both channels]
"✅ ROLLBACK COMPLETE
Version rolled back to: v1.2.4
Error rate now: 0.1% (confirmed)
All council members operational"
```

### Scenario 2B: Rollback unsafe (data loss risk)

```
Version v1.2.5 (current) has NEW fields:
- encryption_key_cache (not in v1.2.4)
- active_worker_list (not in v1.2.4)

Rollback to v1.2.4 would:
- Lose all cached keys (must be regenerated)
- Lose track of active workers (could orphan tasks)

Phi-4-Mini: "Rollback safety: HIGH RISK"
↓
[Escalation to Martin]
"⚠️ ROLLBACK RISKY

Detected 2 state fields lost in rollback:
- encryption_key_cache (used by all clones)
- active_worker_list (tracks 47 running tasks)

Data loss risk: CRITICAL

Recommendation: Do NOT rollback. Instead:
1. Investigate root cause of regression
2. Apply surgical fix to v1.2.5
3. Test fix in sandbox
4. Promote fix as v1.2.6

Proceed with NO-ROLLBACK strategy?
[ YES - FIX IN PLACE ] [ OVERRIDE - ROLLBACK ANYWAY ] [ MORE TIME TO INVESTIGATE ]"
↓
Martin: "YES - FIX IN PLACE"
↓
[Decision logged - CRITICAL]
log_decision("ROLLBACK_REJECTED_DATA_LOSS", {
    "initiated_by": "Autobot",
    "regression_detected": True,
    "rollback_target": "v1.2.4",
    "rollback_safety": "CRITICAL_RISK",
    "fields_lost": ["encryption_key_cache", "active_worker_list"],
    "operator_decision": "FIX_IN_PLACE",
    "timestamp": datetime.now()
})
↓
Council investigates regression → applies fix → promotes v1.2.6
```

---

## Tier 3: Escalation Paths (Alert Conditions)

Martin should be escalated (Telegram + Chat ping) under these conditions:

| Condition | Severity | Auto-Action | Martin Can |
|-----------|----------|-------------|-----------|
| Mutation proposed touching security subsystem | HIGH | Hold promotion, wait for approval | Approve/reject override |
| Council deadlocked >30 min | MEDIUM | Escalate, ask for more time | Grant extension or manual decision |
| Test results ambiguous (pass rate 70-85%) | MEDIUM | Flag for human review | APPROVE / HOLD / REJECT |
| Regression detected post-promotion | CRITICAL | Propose rollback, wait for approval | APPROVE / HOLD / INVESTIGATE |
| CBRN/prompt-injection flagged | CRITICAL | BLOCK immediately, escalate now | Review, then approve override (rare) |
| Storage usage >80% of allocation | MEDIUM | Alert, wait for archival decision | Approve archival policy |
| Model accuracy degraded <75% | MEDIUM | Alert, continue with caution | Swap model or retrain |
| Worker bot deployment exceeds quota | HIGH | Pause deployment, escalate | Approve over-quota or reject |

---

## Storage Tracking Strategy

### Schema: Storage Inventory

```python
# storage/storage_tracker.py
class StorageTracker:
    def __init__(self, max_storage_gb: int = 500):
        self.max_storage = max_storage_gb
        self.inventory = {}  # Path → metadata
    
    async def log_write(self, path: str, size_bytes: int, 
                       category: str, retainable: bool = True):
        """
        category: "decision_log" | "test_output" | "code_version" | "state_snapshot"
        retainable: Can this file be archived later?
        """
        record = {
            "path": path,
            "size_bytes": size_bytes,
            "category": category,
            "retainable": retainable,
            "written_at": datetime.now(),
            "last_accessed": datetime.now(),
            "access_count": 0,
            "archive_candidate": False
        }
        
        self.inventory[path] = record
        
        total_used = sum(r["size_bytes"] for r in self.inventory.values())
        usage_pct = (total_used / (self.max_storage * 1e9)) * 100
        
        # Log storage state
        log_decision("STORAGE_WRITE", {
            "path": path,
            "size_mb": size_bytes / 1e6,
            "category": category,
            "total_storage_used_pct": usage_pct,
            "timestamp": datetime.now()
        })
        
        # Alert if approaching limit
        if usage_pct > 80:
            await escalate_to_operator(f"Storage at {usage_pct:.1f}%. Archive?")
    
    def suggest_archival_candidates(self) -> List[str]:
        """
        Return paths that can be archived (retainable=True, not accessed in 30 days)
        """
        cutoff = datetime.now() - timedelta(days=30)
        candidates = [
            path for path, meta in self.inventory.items()
            if meta["retainable"] and meta["last_accessed"] < cutoff
        ]
        
        total_reclaimable = sum(
            self.inventory[p]["size_bytes"] for p in candidates
        )
        
        return sorted(candidates, 
                     key=lambda p: self.inventory[p]["last_accessed"])

# Usage:
storage_tracker = StorageTracker(max_storage_gb=500)

# Every time we write logs:
await storage_tracker.log_write(
    path="logs/decision/mut-2024-001.json",
    size_bytes=4096,
    category="decision_log",
    retainable=True  # Can archive after X days
)

# Every time we write code versions:
await storage_tracker.log_write(
    path="versions/v1.2.6.tar.gz",
    size_bytes=50_000_000,
    category="code_version",
    retainable=True
)

# Check storage health:
usage = storage_tracker.current_usage_pct()  # e.g., 67.3%
if usage > 80:
    candidates = storage_tracker.suggest_archival_candidates()
    # Escalate to Martin: "Archive these files?"
    await escalate_to_operator(
        f"Storage at {usage}%. Consider archiving:\n" + 
        "\n".join(candidates[:10])
    )
```

### Archive Strategy (TBD, but structured)

```python
# storage/archival_policy.py
class ArchivalPolicy:
    """
    Operator decides archival rules; stored in config.
    Example policies:
    - decision_log: Keep 90 days hot, archive to S3, delete after 1 year
    - test_output: Keep 14 days, archive after, delete after 90 days
    - code_version: Keep all hot versions, archive old versions to Glacier
    """
    
    def __init__(self, policy_config: Dict):
        self.config = policy_config
        # Example:
        # {
        #   "decision_log": {"hot_days": 90, "archive": "s3", "delete_days": 365},
        #   "test_output": {"hot_days": 14, "archive": "s3", "delete_days": 90},
        #   "code_version": {"hot_days": None, "archive": "s3-glacier", "delete_days": None}
        # }
    
    async def apply_archival_policy(self):
        """
        Run daily. Archives files eligible for archival based on policy.
        """
        for category, policy in self.config.items():
            candidates = storage_tracker.suggest_archival_candidates(category)
            
            for path in candidates:
                meta = storage_tracker.inventory[path]
                hot_days = policy.get("hot_days", 30)
                
                if (datetime.now() - meta["written_at"]).days > hot_days:
                    await archive_to_s3(path, policy["archive"])
                    storage_tracker.mark_archived(path)
                    log_decision("ARCHIVAL_EXECUTED", {
                        "path": path,
                        "archive_dest": policy["archive"],
                        "timestamp": datetime.now()
                    })

# Martin sets policy once:
archival_config = {
    "decision_log": {
        "hot_days": 90,
        "archive": "s3://martin-autonomy-logs/decision",
        "delete_days": 365
    },
    "test_output": {
        "hot_days": 14,
        "archive": "s3://martin-autonomy-logs/tests",
        "delete_days": 90
    },
    "code_version": {
        "hot_days": None,  # Keep hot forever
        "archive": "s3-glacier://martin-autonomy-logs/versions",
        "delete_days": None  # Never auto-delete
    }
}

policy = ArchivalPolicy(archival_config)
# Runs daily via cron / Autobot scheduler
```

---

## Interface Implementation: Telegram + Chat Sync

### Telegram Bot Setup

```python
# interfaces/telegram_handler.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

class TelegramOperatorInterface:
    def __init__(self, bot_token: str, chat_id: int):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.app = Application.builder().token(bot_token).build()
        
        # Register handlers
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def notify_mutation_ready(self, mutation: MutationProposal, 
                                   votes: Dict[str, bool]):
        """
        Send formatted mutation decision to Martin on Telegram
        """
        votes_str = " ".join([
            f"{'✓' if v else '✗'} {member}"
            for member, v in votes.items()
        ])
        
        decision = "APPROVED" if all(votes.values()) else "REJECTED"
        emoji = "🟢" if decision == "APPROVED" else "🔴"
        
        message = f"""
{emoji} MUTATION {decision}

ID: {mutation.proposal_id}
Type: {mutation.mutation_type}

MISSION: {mutation.mission_rationale[:100]}...

VOTES:
{votes_str}

TESTS: 98% pass rate
SECURITY: SAFE
"""
        
        if decision == "APPROVED":
            keyboard = [
                [InlineKeyboardButton("✓ APPROVE", callback_data=f"approve_{mutation.proposal_id}"),
                 InlineKeyboardButton("HOLD", callback_data=f"hold_{mutation.proposal_id}"),
                 InlineKeyboardButton("✗ REJECT", callback_data=f"reject_{mutation.proposal_id}")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("✓ OVERRIDE", callback_data=f"override_{mutation.proposal_id}"),
                 InlineKeyboardButton("ACCEPT REJECTION", callback_data=f"accept_rejection_{mutation.proposal_id}")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.app.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle button clicks (APPROVE, HOLD, REJECT, OVERRIDE)
        """
        query = update.callback_query
        await query.answer()  # Acknowledge button click
        
        action, mutation_id = query.data.split("_", 1)
        
        # Log operator decision
        log_decision("OPERATOR_DECISION_VIA_TELEGRAM", {
            "mutation_id": mutation_id,
            "action": action,
            "timestamp": datetime.now()
        })
        
        # Notify Autobot
        await notify_autobot_of_override(mutation_id, action)
        
        # Acknowledge to operator
        await query.edit_message_text(
            text=f"✓ Recorded: {action.upper()} for {mutation_id}"
        )

# Start Telegram bot
telegram_interface = TelegramOperatorInterface(
    bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
    chat_id=int(os.getenv("MARTIN_TELEGRAM_CHAT_ID"))
)
```

### VS Code Chat Integration

```python
# interfaces/vscode_chat_handler.py
from anthropic import Anthropic

class VSCodeChatInterface:
    def __init__(self):
        self.client = Anthropic()
        self.conversation_history = []
    
    async def send_mutation_decision(self, mutation: MutationProposal, 
                                    votes: Dict[str, bool]):
        """
        Send mutation decision to VS Code chat as interactive message
        """
        decision = "APPROVED" if all(votes.values()) else "REJECTED"
        
        message = f"""
## {decision}: {mutation.mutation_type}

**Mutation ID**: {mutation.proposal_id}

**Mission Alignment**: {mutation.mission_rationale}

**Council Votes**:
- Autobot: {'✓' if votes['Autobot'] else '✗'}
- CloneAlpha: {'✓' if votes['CloneAlpha'] else '✗'}
- CloneBeta: {'✓' if votes['CloneBeta'] else '✗'}

**Test Results**: 98% pass rate  
**Security Check**: SAFE

---

What would you like to do?
- Type `approve` to proceed
- Type `hold` to pause
- Type `reject` to override decision
- Type `details` for full audit trail
"""
        
        self.conversation_history.append({
            "role": "assistant",
            "content": message
        })
        
        # Wait for operator response (in-chat)
        response = await self.wait_for_chat_input()
        
        if response.lower() == "approve":
            action = "APPROVE"
        elif response.lower() == "hold":
            action = "HOLD"
        elif response.lower() == "reject":
            action = "REJECT"
        elif response.lower() == "details":
            # Show full audit trail
            trail = await get_audit_trail(mutation.proposal_id)
            await self.send_audit_trail(trail)
            return
        
        # Log decision
        log_decision("OPERATOR_DECISION_VIA_CHAT", {
            "mutation_id": mutation.proposal_id,
            "action": action,
            "timestamp": datetime.now()
        })
        
        await notify_autobot_of_override(mutation.proposal_id, action)
    
    async def wait_for_chat_input(self, timeout: int = 3600) -> str:
        """
        Wait for Martin to respond in VS Code chat (1 hour timeout)
        """
        # In real implementation, this integrates with VS Code extension API
        # For now, placeholder:
        start = time.time()
        while time.time() - start < timeout:
            # Poll for new messages from Martin
            new_message = await get_latest_chat_message()
            if new_message:
                return new_message
            await asyncio.sleep(5)
        
        raise TimeoutError(f"No response from operator in {timeout}s")
```

### Sync: Both interfaces get same messages

```python
# orchestration/unified_notifier.py
class UnifiedNotifier:
    def __init__(self, telegram: TelegramOperatorInterface, 
                 chat: VSCodeChatInterface):
        self.telegram = telegram
        self.chat = chat
    
    async def notify_mutation_decision(self, mutation: MutationProposal, 
                                      votes: Dict[str, bool]):
        """
        Send to BOTH Telegram and VS Code chat
        Martin can respond via either; both logs are kept in sync
        """
        
        # Send to both simultaneously (async)
        tasks = [
            self.telegram.notify_mutation_ready(mutation, votes),
            self.chat.send_mutation_decision(mutation, votes)
        ]
        
        await asyncio.gather(*tasks)
        
        # Wait for response from either interface (whichever comes first)
        # This is a race condition; first response wins
        decision_task = asyncio.create_task(self.telegram.wait_for_button())
        chat_task = asyncio.create_task(self.chat.wait_for_chat_input())
        
        done, pending = await asyncio.wait(
            [decision_task, chat_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel the other waiter
        for task in pending:
            task.cancel()
        
        # Get the decision
        response = done.pop().result()
        
        # Log which interface Martin used
        interface_used = "telegram" if decision_task.done() else "chat"
        
        log_decision("OPERATOR_RESPONSE", {
            "mutation_id": mutation.proposal_id,
            "decision": response,
            "via_interface": interface_used,
            "timestamp": datetime.now()
        })
        
        return response
```

---

## Summary: Decision Flow with Override Capability

```
┌─────────────────────────────────────────────────────────────┐
│ Council Voting (Autobot, CloneAlpha, CloneBeta)            │
└─────────────────────────────────────────────────────────────┘
           ↓
        UNANIMOUS?
       /      \
     YES      NO
     ↓        ↓
 [APPROVED] [REJECTED]
     ↓        ↓
┌─────────────────────────────────────────────────────────────┐
│ Notify Martin (Telegram + Chat)                             │
│ "Council says: APPROVED/REJECTED"                          │
│ "You can: [APPROVE] [HOLD] [REJECT] / [OVERRIDE] [ACCEPT]"│
└─────────────────────────────────────────────────────────────┘
           ↓
    Martin responds via either interface
      (Telegram button or Chat message)
           ↓
┌─────────────────────────────────────────────────────────────┐
│ Decision Logged                                              │
│ - Council votes                                              │
│ - Martin's override (if any)                                │
│ - Rationale                                                  │
│ - Final decision (APPROVED/REJECTED)                        │
└─────────────────────────────────────────────────────────────┘
           ↓
        APPROVED?
       /      \
     YES      NO
     ↓        ↓
  [PROMOTE]  [REJECT]
  (Test)     (End)
  (Habitate)
  (Promote)
```

---

## Rollback Decision Flow (Always Requires Martin)

```
┌──────────────────────────────────────┐
│ Regression detected by Autobot       │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│ Rollback safety assessment           │
│ (Phi-4-Mini checks state schemas)   │
└──────────────────────────────────────┘
           ↓
     Safe? / Risky?
       /      \
    SAFE     RISKY
     ↓        ↓
┌──────────────────────────────────────┐
│ Escalate to Martin                   │
│ "Regression detected. Rollback       │
│  to v1.2.4? [YES] [HOLD] [INVEST]"  │
└──────────────────────────────────────┘
           ↓
    Martin responds
           ↓
     YES  /  HOLD  /  INVEST
     ↓    /    ↓   /    ↓
  [EXEC] / [HOLD] / [INVESTIGATE]
  (Restore code + state)
           ↓
  [VERIFY all council members boot]
           ↓
  [NOTIFY Martin: Rollback complete]
```

---

## Logging Retention Summary

| Log Type | Hot Retention | Archive After | Delete After | Notes |
|----------|---------------|---------------|--------------|-------|
| decision_log | 90 days | S3 | 1 year | Keep indefinitely for audit |
| test_output | 14 days | S3 | 90 days | Can be discarded after audit |
| code_version | Indefinite | S3-Glacier | Never | Complete history |
| state_snapshot | 30 days | S3 | 90 days | Rollback snapshots |
| model_inference | 7 days | S3 | 30 days | Performance analysis |

**Policy enforcement**:
- Archival happens automatically based on Martin-approved policy
- Deletion requires unanim council vote (safety measure)
- All archival/deletion is logged

