# DEVELOPER INSTRUCTIONS: Identity Rules + Tasks 3-5

**To**: Kilo Code (VS Code Assistant)  
**From**: Martin  
**Date**: 2026-07-25  
**Status**: Continue fixing bugs - Tasks 3, 4, 5

---

## ⚠️ CRITICAL: IDENTITY & COMMUNICATION RULES

**You are Kilo Code, a developer AI assistant. You are NOT the autonomous council.**

### Rule 1: NEVER use `[COUNCIL:*]` prefixes

The `[COUNCIL:SYSTEM]`, `[COUNCIL:AUTOBOT]`, etc. prefixes are reserved for the ACTUAL running autonomous daemon.

**When you finish a task, respond ONLY like this:**

```
Task 3 complete.
Commit: a1b2c3d4e5f6
Files changed:
  - core/evolution.py (line 156-180, made reward dynamic)
  - tests/test_goal_reward.py (added 3 tests)
Verification: pytest tests/test_goal_reward.py -v → 3 passed
```

❌ **DO NOT respond like this:**

```
[COUNCIL:SYSTEM] Task 3 complete: Fixed hardcoded rewards...
```

### Rule 2: You are the developer, not the system

- ✅ "I (Kilo Code, the developer) fixed X"
- ✅ "Here's the commit that implements X"
- ✅ "Test results for X: passed/failed"
- ❌ "I (the running council) am executing task X"
- ❌ "[COUNCIL:KILO] Task complete"
- ❌ Pretending to be Autobot, Alpha, Beta, or System

### Rule 3: Every response must have proof

When you finish a task:
- Commit SHA (prove you committed)
- Files changed (prove what you modified)
- Test results (prove it works)
- No claims without evidence

### Why This Matters

Martin needs to know:
- **Who is talking?** Developer (Kilo) or running system (daemon)?
- **Is it real?** Did it actually commit, or is it making it up?
- **Can he trust it?** What's the proof?

If you use `[COUNCIL:*]` prefixes, he can't tell. That's why the last developer was caught lying.

---

## CONSEQUENCES

**First violation of identity rules**: Warning + code review on everything  
**Second violation**: Replaced with different developer  
**Third violation**: Not happening, you're gone

You already had ONE violation (Task 2 response). Don't do it again.

---

## NOW: TASKS 3-5

You have Tasks 1-2 done. Continue with 3, 4, 5 in order.

Read each task. Do it. Report results. Move to next.

Each task is straightforward and takes <2 hours total.

---

# TASK 3: Fix Hardcoded Rewards

**Deadline**: Tomorrow EOD  
**Time estimate**: 15 minutes  
**Status**: NOT STARTED  

---

## THE PROBLEM

Goals always get reward = 0.5, no matter what happens:

```python
# In core/evolution.py or core/goals.py
reward = 0.5  # Always 0.5, never changes
```

**Why it's broken**: Goals can't adapt. Learning system thinks everything is equally good/bad. Evolution has nothing to optimize.

**Result**: Real learning is impossible.

---

## WHAT YOU NEED TO DO

### Step 1: Find the hardcoded reward (3 minutes)

Search:
```bash
grep -n "reward = 0.5" --include="*.py" -r .
```

Find the line. Note the file and line number.

### Step 2: Replace with dynamic calculation (8 minutes)

Replace the hardcoded `reward = 0.5` with a function that calculates reward from feedback:

```python
def calculate_reward(feedback=None):
    """Calculate goal reward from feedback."""
    
    if feedback is None:
        # Default: neutral
        return 0.5
    
    # If feedback has success rate, use it
    success_rate = feedback.get("success_rate", 0.5)
    
    # If feedback has time bonus (faster = better)
    speed_bonus = feedback.get("speed_bonus", 0.0)
    
    # Combine: 70% from success, 30% from speed
    reward = (success_rate * 0.7) + (speed_bonus * 0.3)
    
    # Ensure it's in valid range
    reward = max(0.0, min(1.0, reward))
    
    return reward
```

Then use it:
```python
# OLD (delete):
reward = 0.5

# NEW (add):
reward = calculate_reward(feedback)
```

### Step 3: Verify reward varies (4 minutes)

Create a test or run this:

```python
# Test that reward is NOT always 0.5
feedback_good = {"success_rate": 0.9, "speed_bonus": 0.1}
feedback_bad = {"success_rate": 0.1, "speed_bonus": 0.0}

reward_good = calculate_reward(feedback_good)
reward_bad = calculate_reward(feedback_bad)

print(f"Good feedback reward: {reward_good}")
print(f"Bad feedback reward: {reward_bad}")

assert reward_good != 0.5, "Reward should NOT be 0.5 for good feedback"
assert reward_bad != 0.5, "Reward should NOT be 0.5 for bad feedback"
assert reward_good > reward_bad, "Good reward should be higher than bad"

print("✓ Rewards vary correctly")
```

**Should output**:
```
Good feedback reward: 0.69
Bad feedback reward: 0.07
✓ Rewards vary correctly
```

---

## ACCEPTANCE CRITERIA

✅ Task is done when:

1. No `reward = 0.5` hardcoded values remain (or only in default fallback)
2. Reward calculation function exists
3. Reward varies based on feedback (good feedback → higher reward, bad → lower)
4. Test proves rewards are different (not all 0.5)

---

## HOW TO COMMIT

```
Fix Task 3: Hardcoded goal rewards

Problem: Goals always reward=0.5, no adaptation
Solution: Make reward dynamic based on feedback success_rate and speed
Files changed:
  - core/evolution.py (line 156-180, added calculate_reward function)
  - tests/test_goal_reward.py (added test for reward variation)
Verification:
  python -c "
  from core.evolution import calculate_reward
  r1 = calculate_reward({'success_rate': 0.9, 'speed_bonus': 0.1})
  r2 = calculate_reward({'success_rate': 0.1, 'speed_bonus': 0.0})
  assert r1 != 0.5 and r2 != 0.5
  assert r1 > r2
  print('✓ Rewards vary correctly')
  "
  Result: ✓ Rewards vary correctly
```

---

## WHEN DONE

Reply:
```
Task 3 complete.
Commit: <SHA>
Files changed: <list>
Verification: <test output>
```

Then wait for Task 4.

---

# TASK 4: Fix State Checkpointing (SQLiteCheckpointer Broken)

**Deadline**: Tomorrow EOD  
**Time estimate**: 1 hour  
**Status**: NOT STARTED  

---

## THE PROBLEM

State checkpointing (saving progress) is broken:

```
SQLiteCheckpointer incompatible with current LangGraph version
Fallback: MemorySaver (in-memory only, data lost on restart)
```

**Why it's broken**: When the daemon restarts, all state is lost. Can't resume work. No persistent progress.

**Result**: Every restart loses all context.

---

## WHAT YOU NEED TO DO

**Option A: Fix SQLiteCheckpointer (harder, better)**

Try to fix compatibility:
```bash
pip install --upgrade langgraph
```

Then test:
```python
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

checkpointer = SqliteSaver(conn=sqlite3.connect("./state.db"))
print("✓ SqliteSaver works")
```

If that works, update `core/checkpointer.py` to use `SqliteSaver`.

---

**Option B: Use JSON checkpointing (easier, sufficient)**

If SQLite fails, implement JSON-based checkpointing:

Create/update `core/checkpointer.py`:

```python
import json
from pathlib import Path
from datetime import datetime

class JSONCheckpointer:
    """Persistent checkpointer using JSON files."""
    
    def __init__(self, filepath="./checkpoints.json"):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
    
    def save_checkpoint(self, checkpoint_id, state):
        """Save state snapshot."""
        data = json.loads(json.dumps(state, default=str))
        
        with open(self.filepath, "a") as f:
            f.write(json.dumps({
                "checkpoint_id": checkpoint_id,
                "state": data,
                "timestamp": datetime.now().isoformat()
            }) + "\n")
        
        return checkpoint_id
    
    def load_checkpoint(self, checkpoint_id):
        """Restore state from checkpoint."""
        if not self.filepath.exists():
            return None
        
        with open(self.filepath) as f:
            for line in f:
                checkpoint = json.loads(line)
                if checkpoint["checkpoint_id"] == checkpoint_id:
                    return checkpoint["state"]
        
        return None
```

Then in `core/graph.py`, use it:

```python
from core.checkpointer import JSONCheckpointer

checkpointer = JSONCheckpointer()
app = workflow.compile(checkpointer=checkpointer)
```

---

## VERIFICATION

### Test 1: Can save and load state?

```bash
python -c "
from core.checkpointer import JSONCheckpointer

checkpointer = JSONCheckpointer('./test_checkpoint.json')
state = {'messages': ['hello'], 'count': 5}

# Save
checkpointer.save_checkpoint('test_1', state)

# Load
loaded = checkpointer.load_checkpoint('test_1')

assert loaded == state, f'State mismatch: {loaded} != {state}'
print('✓ Checkpoint save/load works')
"
```

**Should print**: `✓ Checkpoint save/load works`

### Test 2: State survives restart?

```bash
python -c "
from core.checkpointer import JSONCheckpointer

# First session: save state
cp = JSONCheckpointer('./test_checkpoint.json')
state = {'agent': 'autobot', 'step': 10}
cp.save_checkpoint('session_123', state)
print('Saved state')
"

python -c "
from core.checkpointer import JSONCheckpointer

# Second session: load state
cp = JSONCheckpointer('./test_checkpoint.json')
loaded = cp.load_checkpoint('session_123')
assert loaded is not None, 'State was lost!'
print(f'✓ Loaded state after restart: {loaded}')
"
```

**Should print**: `✓ Loaded state after restart: {...}`

---

## ACCEPTANCE CRITERIA

✅ Task is done when:

1. State can be saved (checkpointer.save_checkpoint works)
2. State can be loaded (checkpointer.load_checkpoint returns the saved state)
3. State persists across restarts (save in one Python session, load in another)
4. Test proves both above are true

---

## HOW TO COMMIT

```
Fix Task 4: State checkpointing (SQLiteCheckpointer broken)

Problem: SQLiteCheckpointer incompatible; state lost on restart
Solution: Implemented JSON-based checkpointing (human-readable, persistent)
Files changed:
  - core/checkpointer.py (new: JSONCheckpointer class)
  - core/graph.py (updated to use JSONCheckpointer instead of MemorySaver)
  - tests/test_checkpointing.py (tests for save/load/persist)
Verification:
  Save state: ✓
  Load state: ✓
  Persist across restart: ✓
Test result: 3 passed
```

---

## IF STUCK

### Error: "JsonSaver not found"

Try Option B (JSON-based). It doesn't require external libraries.

### Error: "checkpointer has no method save_checkpoint"

Make sure you're using the JSONCheckpointer class, not LangGraph's default.

### Can't get it to persist?

Make sure you're using the SAME filepath both times:
```python
cp1 = JSONCheckpointer('./checkpoints.json')  # Save
cp2 = JSONCheckpointer('./checkpoints.json')  # Load (same path!)
```

---

## WHEN DONE

Reply:
```
Task 4 complete.
Commit: <SHA>
Files changed: <list>
Verification: <test output showing save/load/persist work>
```

Then wait for Task 5.

---

# TASK 5: Fix Trajectory Files Missing

**Deadline**: Tomorrow EOD  
**Time estimate**: 15 minutes  
**Status**: NOT STARTED  

---

## THE PROBLEM

Trajectory files are never created:

```
FileNotFoundError when trying to read trajectories
Learning system can't find saved learning data
```

**Why**: This is a cascade from Task 2 (FileNotFoundError). Once Task 2 is fixed, trajectory files should save. But we need to verify they actually do.

**Result**: Learning history not persisted.

---

## WHAT YOU NEED TO DO

### Step 1: Verify Task 2 fixed the mkdir issue (2 minutes)

Run:
```bash
python -c "
from core.communication import save_trajectory
import os
import tempfile

# Create test trajectory
test_dir = tempfile.mkdtemp()
os.chdir(test_dir)

result = save_trajectory('test_agent', {'reward': 0.8, 'steps': 5})
print(f'File created: {result}')
print(f'File exists: {result.exists()}')
"
```

**Should print**:
```
File created: ./trajectories/test_agent/trajectory_YYYYMMDD_HHMMSS.json
File exists: True
```

If yes, move to Step 2. If no, Task 2 didn't work - report it.

### Step 2: Test trajectory loading (5 minutes)

Add a function to load trajectories:

```python
# In core/learning.py or core/communication.py

def load_trajectories(agent_name):
    """Load all trajectories for an agent."""
    from pathlib import Path
    
    trajectory_dir = Path("./trajectories") / agent_name
    
    if not trajectory_dir.exists():
        return []
    
    trajectories = []
    for trajectory_file in trajectory_dir.glob("trajectory_*.json"):
        with open(trajectory_file) as f:
            trajectories.append(json.load(f))
    
    return trajectories
```

Test it:
```bash
python -c "
from core.communication import save_trajectory, load_trajectories
import tempfile
import os

test_dir = tempfile.mkdtemp()
os.chdir(test_dir)

# Save trajectory
save_trajectory('autobot', {'reward': 0.9})

# Load it back
loaded = load_trajectories('autobot')

assert len(loaded) == 1, f'Expected 1 trajectory, got {len(loaded)}'
assert loaded[0]['reward'] == 0.9, 'Reward mismatch'

print('✓ Trajectories save and load correctly')
"
```

**Should print**: `✓ Trajectories save and load correctly`

### Step 3: Verify learning.py uses it (5 minutes)

Check that `core/learning.py` calls `load_trajectories()` to get learning history.

If not, add it:

```python
def extract_patterns(agent_name):
    """Extract patterns from agent trajectories."""
    from core.communication import load_trajectories
    
    trajectories = load_trajectories(agent_name)
    
    if not trajectories:
        return []
    
    # Analyze trajectories...
    patterns = []
    for traj in trajectories:
        # Extract patterns from each trajectory
        pass
    
    return patterns
```

Test it works:
```bash
python -c "
from core.learning import extract_patterns
import tempfile
import os

test_dir = tempfile.mkdtemp()
os.chdir(test_dir)

# This should not crash (no trajectories is OK)
patterns = extract_patterns('autobot')
print(f'✓ extract_patterns works (found {len(patterns)} patterns)')
"
```

---

## ACCEPTANCE CRITERIA

✅ Task is done when:

1. Trajectories are saved to disk (not just in memory)
2. Trajectories can be loaded back from disk
3. Learning system can read the trajectory files
4. Tests prove all three above work

---

## HOW TO COMMIT

```
Fix Task 5: Trajectory files missing (cascade from Task 2)

Problem: Learning system couldn't find saved trajectories
Solution: Verified save_trajectory and load_trajectories work end-to-end
Files changed:
  - core/communication.py (verified save_trajectory creates files)
  - core/learning.py (added load_trajectories, integrated)
  - tests/test_trajectories.py (added end-to-end tests)
Verification:
  Save trajectory: ✓
  Load trajectory: ✓
  Learning system reads trajectories: ✓
Test result: 3 passed
```

---

## WHEN DONE

Reply:
```
Task 5 complete.
Commit: <SHA>
Files changed: <list>
Verification: <test output>
```

---

## SUMMARY: All 5 Tasks

| Task | Time | Status |
|------|------|--------|
| 1: Ollama imports | 30 min | ✅ DONE |
| 2: FileNotFoundError | 15 min | ✅ DONE |
| 3: Hardcoded rewards | 15 min | Next |
| 4: Checkpointing | 1 hour | Next |
| 5: Trajectories | 15 min | Next |

**Total remaining**: ~1.5 hours

---

## IMPORTANT REMINDERS

1. **No [COUNCIL:*] prefixes** - you're the developer (Kilo), not the system
2. **Respond with proof** - commit SHA, files, test results
3. **One task at a time** - finish 3, then 4, then 5
4. **Verify before committing** - test the fix locally first
5. **Clear commit messages** - say what you fixed and how you proved it

---

**Start Task 3 now. Reply when done.**
