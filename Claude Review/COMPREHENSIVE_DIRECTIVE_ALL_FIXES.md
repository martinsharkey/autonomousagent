# COMPREHENSIVE DIRECTIVE: All Pipeline Fixes for Mission-Aligned Autonomy

**FROM**: Martin (operator)  
**TO**: Kilo (developer)  
**DATE**: 2026-07-29  
**PRIORITY**: High  
**SCOPE**: Three major fixes to enable real evolution  
**TIMELINE**: 4-6 hours total (do in order)  

---

## CONTEXT

The council is now safe (SAGA + safety gates work) but sterile (doing fake maintenance goals instead of advancing mission pillars). Three fixes are needed to restore meaningful autonomy while keeping safety:

1. **Mission Governor** - Guide mutations toward mission pillars
2. **Safety Gate Relaxation** - Allow non-critical files to be auto-modified
3. **Git Notification Surface** - Prove mutations actually happened via git commits

---

## FIX #1: MISSION GOVERNOR (90 minutes)

**GOAL**: Before proposing any mutation, check if it advances one of the 5 mission pillars.

**FILES TO CREATE/MODIFY**:
- Create: `core/mission_governor.py` (new file)
- Modify: `core/mutation_proposer.py` (import and call governor)
- Modify: `core/evolution.py` (use governor before proposing)

---

### STEP 1a: Create core/mission_governor.py

```python
"""Mission Governor - Evaluates if mutations serve the 5 mission pillars."""

from typing import Tuple, Optional

MISSION_PILLARS = {
    1: "Recursive Self-Evolution",
    2: "Autonomous Resource Optimization",
    3: "Model Agnosticism",
    4: "Durable Local State",
    5: "Companion Alignment"
}

PILLAR_KEYWORDS = {
    1: [
        "evolution.py", "mutation_proposer.py", "agents/",
        "improve mutation", "better proposal", "code quality",
        "detection", "anti-pattern", "self-improve"
    ],
    2: [
        "api_router.py", "quota_monitor.py", "provider", "cost",
        "optimize routing", "minimize api", "free-tier", "batching",
        "request optimization", "quota-aware"
    ],
    3: [
        "providers.yaml", "model support", "new provider", "failover",
        "model agnostic", "multi-model", "provider test"
    ],
    4: [
        "checkpointer.py", "goals.py", "persistence", "state recovery",
        "durable", "snapshot", "recover", "local state"
    ],
    5: [
        "telegram.py", "operator control", "interface", "command",
        "override", "manual", "approval"
    ]
}

def check_mission_alignment(mutation_description: str, mutation_type: str, target_files: list) -> Tuple[bool, Optional[int], str]:
    """
    Check if mutation aligns with mission pillars.
    
    Args:
        mutation_description: What the mutation does (from proposer)
        mutation_type: Type of mutation (parameter_adjustment, file_addition, etc)
        target_files: List of files the mutation touches
    
    Returns:
        (is_aligned, pillar_number, reason)
        - is_aligned: True if mutation serves a pillar
        - pillar_number: 1-5 if aligned, None if not
        - reason: Explanation of why/why not
    """
    
    # Check if this is maintenance/busy work
    is_maintenance = any(
        word in mutation_description.lower()
        for word in ["maintenance", "cycle", "housekeeping", "cleanup", "routine"]
    )
    if is_maintenance and not any(
        word in mutation_description.lower()
        for word in ["improve", "optimize", "enhance", "fix", "repair"]
    ):
        return False, None, "Maintenance cycles are not mission-aligned"
    
    # Check each pillar
    combined_text = (mutation_description + " " + mutation_type + " " + " ".join(target_files)).lower()
    
    for pillar_num, keywords in PILLAR_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw.lower() in combined_text)
        if matches >= 2:  # At least 2 keywords match
            pillar_name = MISSION_PILLARS[pillar_num]
            return True, pillar_num, f"Aligns with Pillar {pillar_num} ({pillar_name})"
    
    # Not aligned with any pillar
    return False, None, "Does not advance any mission pillar"


def get_mission_alignment_score(pillar: int) -> int:
    """Bonus quality score for mission-aligned mutations."""
    # Mission-aligned mutations get quality boost
    alignment_bonus = {
        1: 15,  # Self-evolution is highest priority
        2: 12,  # Resource optimization
        3: 10,  # Model agnosticism
        4: 8,   # Durable state
        5: 5    # Companion (lower priority)
    }
    return alignment_bonus.get(pillar, 0)
```

---

### STEP 1b: Modify core/mutation_proposer.py

**LOCATION**: At the top of file, add import:
```python
from core.mission_governor import check_mission_alignment, get_mission_alignment_score
```

**LOCATION**: In the `propose_mutation()` function, after proposal is generated (around line ~200)

**ADD THIS** (before returning proposal):
```python
    # NEW: Check mission alignment
    is_aligned, pillar, alignment_reason = check_mission_alignment(
        mutation_description=proposal.get("description", ""),
        mutation_type=proposal.get("mutation_type", ""),
        target_files=proposal.get("file_changes", [])
    )
    
    if not is_aligned:
        # Reject non-aligned proposals
        print(f"[PROPOSER] Rejected non-aligned proposal: {alignment_reason}")
        return None
    
    # Add mission details to proposal
    proposal["mission_pillar"] = pillar
    proposal["mission_alignment_reason"] = alignment_reason
    
    # Bonus quality score for mission-aligned
    pillar_bonus = get_mission_alignment_score(pillar)
    proposal["quality_score"] = min(100, proposal.get("quality_score", 60) + pillar_bonus)
    
    print(f"[PROPOSER] Accepted mission-aligned proposal: Pillar {pillar} (+{pillar_bonus} quality)")
    return proposal
```

---

### STEP 1c: Verify in core/evolution.py

**CHECK**: That `propose_mutation()` is being called before council votes

Search for line with: `propose_mutation(` in core/evolution.py

Should be somewhere around line 500-600. Confirm it's called before `council_vote()`.

If not wired: Add this call in the right place in the autonomy loop.

---

### TEST FIX #1

After implementing:
```bash
# Check imports work
python3 -c "from core.mission_governor import check_mission_alignment; print('✓ Mission Governor imported')"

# Check a proposal gets rejected if not mission-aligned
# Manually test in console or via daemon logs
tail -50 session_log.md | grep -i "mission_align\|rejected"
# Should show rejections of non-aligned proposals
```

**PASS CRITERIA**:
- ✅ Fake "maintenance cycle" goals are REJECTED by proposer
- ✅ Real mutation proposals mention "Pillar X" in logs
- ✅ Quality scores boosted for mission-aligned mutations

---

## FIX #2: RELAX SAFETY GATE FOR NON-CRITICAL FILES (60 minutes)

**GOAL**: Allow non-critical files to be modified by council if mission-aligned + safe.

**FILE TO MODIFY**: `core/mutation_safety_gate.py`

---

### STEP 2a: Expand CRITICAL_FILES list and add AUTO_ALLOWED

**LOCATION**: Lines ~30-50 (where CRITICAL_FILES is defined)

**CURRENT CODE**:
```python
CRITICAL_FILES = {
    "core/agent_loop.py",
    "core/api_router.py",
    "core/evolution.py",
    # ... etc
}
```

**REPLACE WITH**:
```python
# Files that MUST require human approval before modification
CRITICAL_FILES = {
    "core/agent_loop.py",
    "core/api_router.py",
    "core/evolution.py",
    "core/telegram.py",
    "council_daemon.py",
    "core/state.py",
    "core/graph.py",
    "core/rollback.py",
    "core/snapshots.py",
    "core/checkpointer.py",
}

# Files that CAN be auto-modified if mission-aligned + safe
AUTO_ALLOWED_PATTERNS = {
    "tools/",          # New tool creation allowed
    "providers.yaml",  # Provider config changes allowed
    "agents/",         # Agent prompt tweaks allowed (not core logic)
    "core/goals.py",   # Goal execution improvements allowed
    "core/quota_monitor.py",  # Quota tracking improvements allowed
}

def is_allowed_for_auto_apply(file_path: str) -> bool:
    """Check if file is allowed for auto-apply (no human approval needed)."""
    if file_path in CRITICAL_FILES:
        return False
    
    for pattern in AUTO_ALLOWED_PATTERNS:
        if file_path.startswith(pattern):
            return True
    
    return False
```

---

### STEP 2b: Update check_mutation_safety() function

**LOCATION**: The main `check_mutation_safety()` function

**FIND THIS SECTION**:
```python
def check_mutation_safety(mutation: Mutation) -> Tuple[bool, str]:
    """Validate mutation before applying."""
    
    for change in mutation.file_changes:
        if change.path in CRITICAL_FILES:
            return False, f"Critical file {change.path} requires human approval"
```

**REPLACE WITH**:
```python
def check_mutation_safety(mutation: Mutation) -> Tuple[bool, str, bool]:
    """
    Validate mutation before applying.
    
    Returns:
        (is_safe, reason, requires_approval)
        - is_safe: Can mutation be applied?
        - reason: Explanation
        - requires_approval: Does it need operator approval?
    """
    
    requires_approval = False
    
    for change in mutation.file_changes:
        if change.path in CRITICAL_FILES:
            # Critical files need approval but are still safe
            requires_approval = True
            continue
        
        if not is_allowed_for_auto_apply(change.path):
            # Not critical but also not in allowed list
            return False, f"File {change.path} not approved for auto-apply", False
        
        # Check syntax for Python files
        if change.path.endswith(".py"):
            try:
                import ast
                ast.parse(change.content)
            except SyntaxError as e:
                return False, f"Syntax error in {change.path}: {e}", False
    
    return True, "Mutation is safe", requires_approval
```

---

### STEP 2c: Wire approval check into evolution

**LOCATION**: In core/evolution.py, in the function that applies mutations

**FIND**: Where `check_mutation_safety()` is called

**CURRENT**: Probably just checks if safe, then applies

**REPLACE WITH**:
```python
is_safe, reason, requires_approval = check_mutation_safety(mutation)

if not is_safe:
    # Unsafe mutation - reject
    mutation.status = MutationStatus.REJECTED
    mutation.rejection_reason = reason
    return False

if requires_approval:
    # Critical files - need operator approval
    mutation.status = MutationStatus.PENDING_APPROVAL
    await send_telegram(f"🔒 Mutation requires approval: {mutation.mutation_id}\n\n{mutation.description}\n\n/approve {mutation.mutation_id}")
    return False  # Don't auto-apply

# Safe + non-critical + mission-aligned = auto-apply
return True
```

---

### TEST FIX #2

After implementing:
```bash
# Check that tools/ is allowed
python3 -c "
from core.mutation_safety_gate import is_allowed_for_auto_apply
print('tools/request_batcher.py:', is_allowed_for_auto_apply('tools/request_batcher.py'))
print('core/api_router.py:', is_allowed_for_auto_apply('core/api_router.py'))
"

# Should print:
# tools/request_batcher.py: True
# core/api_router.py: False
```

**PASS CRITERIA**:
- ✅ `tools/` files can be created
- ✅ `providers.yaml` can be modified
- ✅ Core files still require approval
- ✅ Unknown files are rejected

---

## FIX #3: SURFACE GIT COMMITS IN NOTIFICATIONS (60 minutes)

See: **EXACT_CODE_CHANGES_GIT_NOTIFICATIONS.md**

This surfaces the SAGA + git workflow that already exists. Don't rebuild it, just make notifications show git proof.

**KEY CHANGES**:
1. Capture git commit hash after commit (core/evolution.py line 949)
2. Add `format_mutation_implemented_message()` function (core/telegram.py)
3. Call telegram after mutation completes with git details (core/evolution.py line 1005)

**EXACT CODE**: See linked document

**TEST FIX #3**:
```bash
# Trigger a mutation (via goal or directly)
# Check notification includes: Commit: a1b2c3d
# Verify git:
git log --oneline | grep mutation
git show a1b2c3d
```

**PASS CRITERIA**:
- ✅ Mutation notifications show commit hash
- ✅ Notifications show branch name
- ✅ Notifications show merged/pending status
- ✅ Commit hash is clickable/copyable

---

## IMPLEMENTATION ORDER

### Day 1 (Today):
**MORNING (2-3 hours)**:
1. Fix #1: Mission Governor (create + wire)
2. Test that fake maintenance goals are rejected

**AFTERNOON (1-2 hours)**:
3. Fix #2: Relax safety gate (modify thresholds)
4. Test that `tools/` can be auto-modified

### Day 2 (Tomorrow):
**MORNING (1 hour)**:
5. Fix #3: Surface git commits
6. Test that notifications show commit hashes

---

## TESTING CHECKLIST

After all three fixes:

```bash
# 1. Mission Governor working?
/status
# Should show: Proposed mutations aligned with Pillar X

# 2. Safety gate relaxed?
tail -20 council.log | grep "tools/"
# Should show: tools/* files being created/modified

# 3. Git commits visible?
/status
# Should show: Commit: a1b2c3d in notifications

# 4. Full flow:
# a) Council proposes real mutation (not maintenance)
# b) Mission Governor approves (Pillar X aligned)
# c) Safety gate approves (safe + allowed)
# d) Mutation applies to branch
# e) Tests run
# f) Notification shows: Commit + Branch + Status
# g) git log shows the commit
```

---

## SUCCESS CRITERIA

**Mission Governor Working**:
- ✅ Only mission-aligned mutations proposed
- ✅ Maintenance goals rejected automatically
- ✅ All 5 pillars can be worked on
- ✅ Quality scores boosted for aligned mutations

**Safety Gate Relaxed**:
- ✅ `tools/` files auto-modifiable
- ✅ `providers.yaml` auto-modifiable
- ✅ Core files still protected (require approval)
- ✅ Unknown files still rejected

**Git Commits Surfaced**:
- ✅ Every mutation notification includes commit hash
- ✅ Every mutation includes branch name
- ✅ Merged/pending status visible
- ✅ Operator can verify: `git show {commit_hash}`

---

## ROLLBACK PLAN

If something breaks:

```bash
# Revert to previous commit
git revert {bad_commit}

# Or for safety gate tests:
git checkout core/mutation_safety_gate.py

# Or for mission governor:
git rm core/mission_governor.py
git checkout core/mutation_proposer.py
```

---

## QUESTIONS FOR KILO

**Before starting**:
1. Can you run the full three fixes in one session?
2. Which fix do you want to start with?
3. Do you need any clarification on the code locations?

**After each fix**:
1. Can you show me the test output?
2. Are the logs showing the right messages?
3. Should we adjust thresholds?

---

## FINAL GOAL

After these three fixes, the council will:

✅ **Propose real work** (Mission Governor filters fake goals)  
✅ **Apply code changes** (Safety gate allows non-critical files)  
✅ **Prove it happened** (Git commits visible in notifications)  
✅ **Be auditable** (Martin can verify every change)  
✅ **Actually advance mission pillars** (Pillar 1-5 work progresses)  

---

## START HERE

**For Kilo**:
1. Read this entire directive
2. Open EXACT_CODE_CHANGES_GIT_NOTIFICATIONS.md (for Fix #3)
3. Start with Fix #1: Mission Governor
4. Test after each fix
5. Report back with test results

**For Martin**:
- Send this to Kilo
- Check back in 4-6 hours for status
- Review test results before next steps

---

This is the complete pipeline to restore meaningful autonomy while keeping safety intact.

