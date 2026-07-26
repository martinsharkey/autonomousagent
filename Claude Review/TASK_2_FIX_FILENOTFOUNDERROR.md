# TASK 2: Fix FileNotFoundError (File I/O)

**Assigned to**: Bob  
**Deadline**: Tomorrow EOD  
**Time estimate**: 15 minutes  
**Status**: NOT STARTED  

---

## THE PROBLEM

When the system tries to save trajectory files, it crashes:

```
FileNotFoundError: [Errno 2] No such file or directory: 
'./trajectories/autobot/trajectory_20260725_120530.json'
```

**Why**: Code tries to write to `./trajectories/autobot/` but the directory doesn't exist.

**Result**: Learning data never gets saved. System can't learn.

---

## WHAT YOU NEED TO DO

### Step 1: Find the broken code (2 minutes)

Open file: `core/communication.py`

Find the function that writes files (probably called `save_trajectory` or similar).

Look for a line like:
```python
with open(trajectory_file, "w") as f:
    json.dump(...)
```

### Step 2: Add mkdir BEFORE the write (5 minutes)

Before the `open()` call, add these lines:

```python
from pathlib import Path

# Get the directory path
trajectory_dir = Path("./trajectories") / agent_name
# Create it if it doesn't exist
trajectory_dir.mkdir(parents=True, exist_ok=True)

# NOW you can write
with open(trajectory_file, "w") as f:
    json.dump(...)
```

**Full example** (if your code looks different, adapt):

```python
import json
from pathlib import Path

def save_trajectory(agent_name, trajectory_data):
    """Save agent trajectory to file."""
    
    # Create directory (FIX: this was missing)
    trajectory_dir = Path("./trajectories") / agent_name
    trajectory_dir.mkdir(parents=True, exist_ok=True)
    
    # Now write the file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trajectory_file = trajectory_dir / f"trajectory_{timestamp}.json"
    
    with open(trajectory_file, "w") as f:
        json.dump(trajectory_data, f, indent=2)
    
    return trajectory_file
```

**What that does**:
- `Path("./trajectories") / agent_name` = `./trajectories/autobot`
- `.mkdir(parents=True, exist_ok=True)` = Create directory (and parents) if needed, don't fail if it exists
- Then write the file

### Step 3: Verify it works (5 minutes)

Run this test:

```bash
python -c "
from core.communication import save_trajectory
import tempfile
import os
os.chdir(tempfile.gettempdir())
result = save_trajectory('autobot', {'test': 'data'})
print(f'✓ File saved: {result}')
print(f'✓ File exists: {result.exists()}')
"
```

**Should print**:
```
✓ File saved: ./trajectories/autobot/trajectory_YYYYMMDD_HHMMSS.json
✓ File exists: True
```

If it prints that, you're done.

### Step 4: Check for other write locations (3 minutes)

Search for other places that might write files:

```bash
grep -r "with open" --include="*.py" | grep -E "(w|a)[\'\"]"
```

If you find other places writing to directories that might not exist, add mkdir there too.

Common places:
- `core/learning.py` - saving trajectories
- `core/communication.py` - sending/saving data
- `storage/storage_tracker.py` - logging writes

For each one, add `mkdir` before the `open()` call.

---

## ACCEPTANCE CRITERIA

✅ Task is done when ALL of these are true:

1. File `core/communication.py` has `mkdir` before the `open()` call
2. `mkdir` uses `parents=True, exist_ok=True`
3. Running the verification command prints `✓ File saved:` and `✓ File exists: True`
4. Any other write locations also have `mkdir` before `open()`

---

## HOW TO COMMIT

When done, commit with this message:

```
Fix Task 2: FileNotFoundError in file I/O

Problem: Code tries to write to trajectories/ but directory doesn't exist
Solution: Add mkdir(parents=True, exist_ok=True) before file writes
Files changed:
  - core/communication.py (added mkdir before write)
  - core/learning.py (added mkdir before write)
  - [any other files with the same issue]
Verification:
  python -c "from core.communication import save_trajectory; ..."
  Result: ✓ File saved and exists
Test: No FileNotFoundError when saving
```

---

## IF YOU GET STUCK

### Error: "trajectory_dir is not defined"

Make sure you're creating it:
```python
trajectory_dir = Path("./trajectories") / agent_name
trajectory_dir.mkdir(parents=True, exist_ok=True)
```

### Error: "Path not imported"

Add at top of file:
```python
from pathlib import Path
```

### Can't find save_trajectory function?

Search:
```bash
grep -r "save_trajectory" --include="*.py"
```

Show me the results.

---

## WHAT NOT TO DO

❌ Don't change how files are named  
❌ Don't change what data is saved  
❌ Don't add new tests (just verify existing code works)  
❌ Don't commit anything else in this commit  
❌ Don't skip checking for other write locations  

---

## WHEN YOU'RE DONE

1. Reply: "Task 2 complete"
2. Paste the output of:
   - The verification command above
   - `git log -1 --oneline` (to show your commit)
3. List which files you fixed
4. I will verify and approve

**Then we move to Task 3.**

---

## ESTIMATED TIME

- Reading this: 5 minutes
- Finding the code: 2 minutes
- Adding mkdir: 5 minutes
- Testing: 3 minutes

**Total: 15 minutes**

---

**Start now. Reply when done.**
