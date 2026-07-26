# PHASE 3: Production Finishing Tasks (9-12)

**To**: Kilo Code  
**Status**: Phase 1-2 complete, ready for final push  
**Objective**: Production-ready system (persistence, security, tests)  
**Total time**: ~2 hours  

---

## IDENTITY REMINDER

You are Kilo Code (developer). NOT the autonomous council.

When you finish each task:
```
Task X complete.
Commit: <SHA>
Test results: <specific numbers>
```

NOT:
```
[COUNCIL:SYSTEM] Task X complete
```

---

# TASK 9: Fix Graph Checkpointer Integration

**Deadline**: Today EOD  
**Time estimate**: 30 minutes  
**Status**: NOT STARTED  
**Priority**: 🔴 CRITICAL - enables state persistence

---

## THE PROBLEM

Currently `core/graph.py` uses MemorySaver (in-memory only):

```python
from langgraph.checkpoint.memory import MemorySaver
# Use MemorySaver for now - SQLite checkpointer integration pending
# TODO: Implement proper BaseCheckpointSaver inheritance for SQLiteCheckpointer
checkpointer = MemorySaver()
```

**Result**: When daemon restarts, all state is lost. No persistence.

**What needs fixing**: Replace MemorySaver with working SQLiteCheckpointer

---

## WHAT YOU NEED TO DO

### Step 1: Replace MemorySaver with SQLiteCheckpointer (10 minutes)

Open `core/graph.py` around line 40-50.

**OLD CODE** (delete this):
```python
from langgraph.checkpoint.memory import MemorySaver

# Use MemorySaver for now - SQLite checkpointer integration pending
# TODO: Implement proper BaseCheckpointSaver inheritance for SQLiteCheckpointer
checkpointer = MemorySaver()
```

**NEW CODE** (add this):
```python
from core.checkpointer import JSONCheckpointer

# Use JSON-based persistent checkpointer
checkpointer = JSONCheckpointer(filepath="./checkpoints.json")
```

### Step 2: Verify imports work (5 minutes)

```bash
python -c "
from core.graph import checkpointer
print(f'✓ Checkpointer type: {type(checkpointer).__name__}')
print(f'✓ Checkpointer is persistent: {hasattr(checkpointer, \"save_checkpoint\")}')
"
```

**Should print**:
```
✓ Checkpointer type: JSONCheckpointer
✓ Checkpointer is persistent: True
```

### Step 3: Test state persists across restart (10 minutes)

Create a test script `test_persistence.py`:

```python
"""Test that state persists across daemon restarts."""

import os
import time
import json
from pathlib import Path

# Clean up any old checkpoint
if Path("./checkpoints.json").exists():
    Path("./checkpoints.json").unlink()

# Session 1: Save state
print("Session 1: Saving state...")
from core.checkpointer import JSONCheckpointer

cp1 = JSONCheckpointer(filepath="./checkpoints.json")
state = {
    "agent": "autobot",
    "step": 42,
    "messages": ["goal created", "executing"]
}
cp1.save_checkpoint("session_test_001", state)
print(f"  Saved: {state}")

# Simulate restart: fresh Python process would start here
print("\nSession 2: Simulating restart...")

# New instance, same file
cp2 = JSONCheckpointer(filepath="./checkpoints.json")
loaded = cp2.load_checkpoint("session_test_001")

if loaded is None:
    print("✗ FAILED: State was lost on restart")
    exit(1)

if loaded == state:
    print(f"  ✓ State restored: {loaded}")
    print("✓ PASSED: State persists across restarts")
else:
    print(f"✗ FAILED: State mismatch")
    print(f"  Expected: {state}")
    print(f"  Got: {loaded}")
    exit(1)
```

Run it:
```bash
python test_persistence.py
```

**Should print**:
```
Session 1: Saving state...
  Saved: {...}
Session 2: Simulating restart...
  ✓ State restored: {...}
✓ PASSED: State persists across restarts
```

### Step 4: Verify checkpoint file is created (5 minutes)

```bash
ls -la checkpoints.json
cat checkpoints.json | head -1
```

**Should show**:
```
-rw-r--r-- 1 user user 325 ... checkpoints.json
{"checkpoint_id": "session_test_001", "state": {...}, "timestamp": "..."}
```

---

## ACCEPTANCE CRITERIA

✅ Task is done when:

1. `core/graph.py` imports JSONCheckpointer (not MemorySaver)
2. `checkpointer = JSONCheckpointer(filepath="./checkpoints.json")`
3. State persists across process restarts (test passes)
4. `checkpoints.json` file is created and contains saved state

---

## HOW TO COMMIT

```
Task 9: Fix graph checkpointer integration

Problem: Graph uses MemorySaver (in-memory), state lost on restart
Solution: Replaced with JSONCheckpointer for persistent state
Files changed:
  - core/graph.py (line ~45, replaced MemorySaver with JSONCheckpointer)
Verification:
  python -c "from core.graph import checkpointer; ..."
  Result: ✓ Checkpointer is JSONCheckpointer
  python test_persistence.py
  Result: ✓ PASSED - State persists across restarts
Test output: Checkpoint file created, state restored correctly
```

---

## WHEN DONE

Reply:
```
Task 9 complete.
Commit: <SHA>
Verification: State persists across restart
```

Then wait for Task 10.

---

# TASK 10: Fix HMAC Secrets (Security Risk)

**Deadline**: Today EOD  
**Time estimate**: 15 minutes  
**Status**: NOT STARTED  
**Priority**: 🔴 CRITICAL - security vulnerability

---

## THE PROBLEM

File `governance/zero_trust.py` has hardcoded default secret:

```python
SECRET_KEY = os.getenv("HMAC_SECRET_KEY", "council_default_secret_key_change_in_production")
```

**Problem**: Default is weak, visible in code, production risk.

**Fix**: Require env var, fail loudly if not set.

---

## WHAT YOU NEED TO DO

### Step 1: Update zero_trust.py (5 minutes)

Open `governance/zero_trust.py`

**OLD CODE** (find and replace):
```python
SECRET_KEY = os.getenv("HMAC_SECRET_KEY", "council_default_secret_key_change_in_production")
```

**NEW CODE**:
```python
SECRET_KEY = os.getenv("HMAC_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError(
        "CRITICAL: HMAC_SECRET_KEY environment variable not set. "
        "Set a strong secret before running: "
        "export HMAC_SECRET_KEY='<your-random-secret-key>'"
    )
```

### Step 2: Test it works (5 minutes)

**Test 1: Without env var (should fail)**
```bash
unset HMAC_SECRET_KEY
python -c "from governance.zero_trust import SECRET_KEY" 2>&1 | head -5
```

**Should output**:
```
ValueError: CRITICAL: HMAC_SECRET_KEY environment variable not set...
```

**Test 2: With env var (should work)**
```bash
export HMAC_SECRET_KEY="my-super-secret-random-key-12345"
python -c "from governance.zero_trust import SECRET_KEY; print('✓ SECRET_KEY loaded')"
```

**Should output**:
```
✓ SECRET_KEY loaded
```

### Step 3: Update .env.example (5 minutes)

Open `.env.example`

Add this line:
```
# SECURITY: Required for HMAC signing of audit logs
# Generate: python -c "import secrets; print(secrets.token_hex(32))"
HMAC_SECRET_KEY=your_super_secret_key_here_change_in_production
```

### Step 4: Update README (optional but good)

Add note to README about secrets:

```markdown
### Security Requirements

Before running in production:
```bash
export HMAC_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
```

You must set HMAC_SECRET_KEY. It will be verified on startup.
```

---

## ACCEPTANCE CRITERIA

✅ Task is done when:

1. `governance/zero_trust.py` requires HMAC_SECRET_KEY (no default)
2. Raises ValueError if not set
3. Works when env var is provided
4. `.env.example` documents HMAC_SECRET_KEY
5. README documents security requirement

---

## HOW TO COMMIT

```
Task 10: Fix HMAC secrets (security)

Problem: Hardcoded default secret in zero_trust.py (production risk)
Solution: Require HMAC_SECRET_KEY env var, fail if not set
Files changed:
  - governance/zero_trust.py (removed default, added validation)
  - .env.example (added HMAC_SECRET_KEY documentation)
  - README.md (added security requirements section)
Verification:
  Without HMAC_SECRET_KEY: ✓ Raises ValueError
  With HMAC_SECRET_KEY: ✓ Works
```

---

## WHEN DONE

Reply:
```
Task 10 complete.
Commit: <SHA>
Verification: HMAC_SECRET_KEY required, fails without it
```

Then wait for Task 11.

---

# TASK 11: Expand .env.example

**Deadline**: Today EOD  
**Time estimate**: 15 minutes  
**Status**: NOT STARTED  
**Priority**: 🟡 MEDIUM - setup clarity

---

## THE PROBLEM

`.env.example` is missing critical variables:
- HMAC_SECRET_KEY (just added in Task 10)
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID
- AUTONOMY_LEVEL
- OLLAMA_MAX_LOADED_MODELS

Result: Users don't know what to configure.

---

## WHAT YOU NEED TO DO

### Step 1: Update .env.example (10 minutes)

Open `.env.example`

Add all missing variables with documentation:

```bash
# ==========================================
# SECURITY & SECRETS
# ==========================================

# HMAC secret for audit log signing
# Generate: python -c "import secrets; print(secrets.token_hex(32))"
HMAC_SECRET_KEY=your_super_secret_key_here_change_in_production

# Telegram bot credentials (required for operator interface)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# ==========================================
# AUTONOMY CONTROL
# ==========================================

# Autonomy level (SAFE / LIMITED / FULL)
# SAFE: Manual approval required for all mutations
# LIMITED: Approve low-risk changes automatically
# FULL: Full autonomous operation
AUTONOMY_LEVEL=SAFE

# ==========================================
# MODEL MANAGEMENT
# ==========================================

# Maximum Ollama models to load at once (memory constraint)
OLLAMA_MAX_LOADED_MODELS=2

# Ollama connection (usually localhost:11434)
OLLAMA_BASE_URL=http://localhost:11434

# ==========================================
# LOGGING & DEBUG
# ==========================================

# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Enable detailed governance audit logging
AUDIT_LOG_VERBOSE=false
```

### Step 2: Verify .env.example is readable (3 minutes)

```bash
cat .env.example | head -30
```

Should show all variables documented.

### Step 3: Verify all env vars are used (2 minutes)

Search code for env var usage:

```bash
grep -r "os.getenv\|os.environ" --include="*.py" core/ governance/ | grep -o '"[A-Z_]*"' | sort -u
```

Compare with .env.example to make sure we're documenting everything.

---

## ACCEPTANCE CRITERIA

✅ Task is done when:

1. `.env.example` contains HMAC_SECRET_KEY
2. `.env.example` contains TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
3. `.env.example` contains AUTONOMY_LEVEL (with options documented)
4. `.env.example` contains OLLAMA_MAX_LOADED_MODELS
5. All variables have inline documentation
6. File is readable and well-organized

---

## HOW TO COMMIT

```
Task 11: Expand .env.example with all required variables

Problem: .env.example missing critical setup variables
Solution: Added HMAC_SECRET_KEY, Telegram, autonomy, and model variables
Files changed:
  - .env.example (added 6+ missing variables with documentation)
Verification:
  cat .env.example | head -30
  Result: All variables documented with inline help
```

---

## WHEN DONE

Reply:
```
Task 11 complete.
Commit: <SHA>
.env.example now has X variables documented
```

Then wait for Task 12.

---

# TASK 12: Integration Test - Control Plane End-to-End

**Deadline**: Tomorrow EOD  
**Time estimate**: 1 hour  
**Status**: NOT STARTED  
**Priority**: 🟡 MEDIUM - system confidence

---

## THE PROBLEM

No end-to-end tests proving the control plane actually works:
- Goal creation → daemon processing → status → feedback
- Goals persist across restarts
- Mutations change agent behavior

Need proof the system works together.

---

## WHAT YOU NEED TO DO

### Step 1: Create integration test file (30 minutes)

Create `tests/test_control_plane_e2e.py`:

```python
"""End-to-end control plane integration test."""

import json
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest


def test_goal_creation_and_persistence():
    """Test creating a goal and verifying it persists."""
    from core.goals import GoalStore
    
    # Create temp database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "goals_test.db"
        
        # Session 1: Create goal
        store1 = GoalStore(db_path=str(db_path))
        goal_id = store1.create_goal(
            description="Test goal",
            priority="high",
            source="test"
        )
        assert goal_id is not None
        
        # Verify goal was saved
        goal = store1.get_goal(goal_id)
        assert goal is not None
        assert goal["description"] == "Test goal"
        assert goal["status"] == "pending"
        
        # Session 2: Simulate restart
        store2 = GoalStore(db_path=str(db_path))
        restored_goal = store2.get_goal(goal_id)
        
        # Verify goal persisted
        assert restored_goal is not None
        assert restored_goal["description"] == "Test goal"
        print("✓ Goal creation and persistence works")


def test_goal_status_updates():
    """Test updating goal status."""
    from core.goals import GoalStore
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "goals_test.db"
        store = GoalStore(db_path=str(db_path))
        
        # Create goal
        goal_id = store.create_goal(
            description="Test status",
            priority="medium",
            source="test"
        )
        
        # Update status
        store.update_status(goal_id, "in_progress")
        goal = store.get_goal(goal_id)
        assert goal["status"] == "in_progress"
        
        # Update again
        store.update_status(goal_id, "completed")
        goal = store.get_goal(goal_id)
        assert goal["status"] == "completed"
        print("✓ Goal status updates work")


def test_goal_priority_ordering():
    """Test goals are ordered by priority."""
    from core.goals import GoalStore
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "goals_test.db"
        store = GoalStore(db_path=str(db_path))
        
        # Create goals with different priorities
        store.create_goal("Low priority", priority="low", source="test")
        store.create_goal("High priority", priority="high", source="test")
        store.create_goal("Medium priority", priority="medium", source="test")
        
        # Get pending goals (should be ordered by priority)
        pending = store.get_pending_goals()
        
        # High priority should be first
        assert pending[0]["priority"] == "high"
        assert pending[1]["priority"] == "medium"
        assert pending[2]["priority"] == "low"
        print("✓ Goal priority ordering works")


def test_autonomy_levels_gating():
    """Test autonomy levels gate mutations."""
    from core.autonomy_levels import check_mutation_allowed, get_current_level
    
    # Test SAFE level requires approval
    level = get_current_level()
    assert level is not None
    
    # In SAFE mode, high-risk mutations should require approval
    can_proceed = check_mutation_allowed(
        mutation_type="config_change",
        risk_level="high",
        autonomy_level="SAFE"
    )
    assert can_proceed == False  # Requires approval
    
    # In FULL mode, should allow
    can_proceed = check_mutation_allowed(
        mutation_type="config_change",
        risk_level="high",
        autonomy_level="FULL"
    )
    assert can_proceed == True
    print("✓ Autonomy level gating works")


def test_health_check_passes():
    """Test health check system."""
    from core.health import run_health_check
    
    result = run_health_check()
    
    # Should return a dict with status info
    assert isinstance(result, dict)
    assert "overall_status" in result or "status" in result
    print("✓ Health check works")


if __name__ == "__main__":
    test_goal_creation_and_persistence()
    test_goal_status_updates()
    test_goal_priority_ordering()
    test_autonomy_levels_gating()
    test_health_check_passes()
    print("\n✓ All integration tests passed")
```

### Step 2: Run the test (15 minutes)

```bash
pytest tests/test_control_plane_e2e.py -v
```

**Should output**:
```
tests/test_control_plane_e2e.py::test_goal_creation_and_persistence PASSED
tests/test_control_plane_e2e.py::test_goal_status_updates PASSED
tests/test_control_plane_e2e.py::test_goal_priority_ordering PASSED
tests/test_control_plane_e2e.py::test_autonomy_levels_gating PASSED
tests/test_control_plane_e2e.py::test_health_check_passes PASSED

====== 5 passed in 0.50s ======
```

If any fail:
- Check error message
- Fix the implementation or the test
- Run again

### Step 3: Add to test suite (5 minutes)

Verify test runs with full suite:

```bash
pytest tests/test_control_plane_e2e.py -v --tb=short
```

All 5 tests should pass.

### Step 4: Document test coverage (5 minutes)

Add comment to top of test file explaining what's being tested:

```python
"""
Integration Tests for Control Plane

This module tests the core autonomous control plane:
1. Goal creation and persistence (SQLite durability)
2. Goal status lifecycle (pending → in_progress → completed)
3. Goal priority ordering (high priority first)
4. Autonomy level risk gating (SAFE/LIMITED/FULL)
5. Health check system

These tests verify the control plane works end-to-end
without requiring the full daemon to be running.
"""
```

---

## ACCEPTANCE CRITERIA

✅ Task is done when:

1. File `tests/test_control_plane_e2e.py` exists
2. Contains at least 5 tests (goal CRUD, status, priority, autonomy, health)
3. All tests pass: `pytest tests/test_control_plane_e2e.py -v` shows 5 passed
4. Tests verify core control plane behavior end-to-end
5. Tests don't require daemon running (pure unit/integration)

---

## HOW TO COMMIT

```
Task 12: Add control plane integration tests

Problem: No tests proving control plane works end-to-end
Solution: Added 5 integration tests covering goal CRUD, persistence, priorities, autonomy gating, health
Files changed:
  - tests/test_control_plane_e2e.py (new: 150 lines)
Verification:
  pytest tests/test_control_plane_e2e.py -v
  Result: 5 passed
Test coverage:
  - Goal creation and persistence: ✓
  - Goal status updates: ✓
  - Goal priority ordering: ✓
  - Autonomy level gating: ✓
  - Health checks: ✓
```

---

## WHEN DONE

Reply:
```
Task 12 complete.
Commit: <SHA>
Test results: 5 passed
```

---

## SUMMARY: Phase 3 Tasks

| Task | Time | Goal |
|------|------|------|
| 9: Checkpointer | 30 min | Enable state persistence |
| 10: HMAC secrets | 15 min | Fix security vulnerability |
| 11: .env.example | 15 min | Setup clarity |
| 12: Integration tests | 1 hour | Prove system works |

**Total**: ~2 hours

**Result**: Production-ready system with:
- ✅ Persistent state (survives restarts)
- ✅ Secure secrets (no hardcoded defaults)
- ✅ Clear configuration (documented .env)
- ✅ Tested control plane (proven end-to-end)

---

## IMPORTANT

1. **Do tasks in order**: 9 → 10 → 11 → 12
2. **Finish one before starting next**
3. **No [COUNCIL:*] prefixes** - you're the developer
4. **Reply with proof** - commit SHA, test numbers
5. **If stuck**: Tell me what's failing

---

**Start Task 9 now. Reply when done.**
