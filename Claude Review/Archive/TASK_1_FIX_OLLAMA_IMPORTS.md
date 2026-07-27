# TASK 1: Fix Ollama Import Errors

**Assigned to**: Bob  
**Deadline**: Tomorrow EOD  
**Time estimate**: 30 minutes  
**Status**: NOT STARTED  

---

## THE PROBLEM

ChatOllama import is failing in multiple places:

```python
# This works sometimes:
from langchain_ollama import ChatOllama

# This works other times:
from langchain_community.chat_models import ChatOllama

# This fails in test context
# Agents can't load models
```

**Result**: Tests fail, agents crash, system can't load LLMs.

---

## WHAT YOU NEED TO DO

### Step 1: Create ONE central import (5 minutes)

Create file: `core/ollama_client.py`

```python
"""Centralized ChatOllama import with fallback."""

try:
    from langchain_ollama import ChatOllama
    print("✓ Using langchain_ollama.ChatOllama")
except ImportError:
    try:
        from langchain_community.chat_models import ChatOllama
        print("✓ Using langchain_community.ChatOllama")
    except ImportError:
        raise ImportError(
            "ChatOllama not found. Install: pip install langchain-ollama"
        )

__all__ = ["ChatOllama"]
```

That's it. Just those lines.

### Step 2: Replace all imports (10 minutes)

Find all files that import ChatOllama:
```bash
grep -r "from langchain" --include="*.py" | grep ChatOllama
```

In each file, replace:
```python
# OLD (delete this line):
from langchain_ollama import ChatOllama
# OR
from langchain_community.chat_models import ChatOllama

# NEW (add this line):
from core.ollama_client import ChatOllama
```

**Files to update** (probably):
- `core/telegram.py`
- `agents/autobot.py`
- `agents/alpha_evaluator.py`
- `agents/beta_worker.py`
- Any others using ChatOllama

### Step 3: Verify it works (10 minutes)

Run this command:
```bash
python -c "from core.ollama_client import ChatOllama; print('✓ Import works')"
```

**Must print**: `✓ Import works`

If it fails, tell me the error.

### Step 4: Run one quick test (5 minutes)

```bash
pytest tests/test_ollama_import.py -v
```

Should show: `1 passed`

If the file doesn't exist, that's OK - continue anyway.

---

## ACCEPTANCE CRITERIA

✅ Task is done when ALL of these are true:

1. File `core/ollama_client.py` exists with the code above
2. `python -c "from core.ollama_client import ChatOllama; print('✓ Import works')"` prints `✓ Import works`
3. All ChatOllama imports in agent files use `from core.ollama_client import ChatOllama`
4. `pytest tests/test_ollama_import.py -v` passes (or shows why test doesn't exist)

---

## HOW TO COMMIT

When done, commit with this message:

```
Fix Task 1: Ollama imports

Problem: ChatOllama import fails in tests; agents can't load models
Solution: Centralized import in core/ollama_client.py with fallback
Files changed:
  - core/ollama_client.py (new file)
  - core/telegram.py (updated import)
  - agents/autobot.py (updated import)
  - agents/alpha_evaluator.py (updated import)
  - agents/beta_worker.py (updated import)
Verification:
  python -c "from core.ollama_client import ChatOllama; print('✓ Import works')"
  Result: ✓ Import works
Test result: 1 passed
```

---

## IF YOU GET STUCK

### Error: "ChatOllama not found in either import"

This means langchain_ollama is not installed. Run:
```bash
pip install langchain-ollama
```

Then try again.

### Error: "pytest: command not found"

```bash
pip install pytest
```

### Can't find all the files that import ChatOllama?

Run:
```bash
grep -r "ChatOllama" --include="*.py"
```

Show me the output.

---

## WHAT NOT TO DO

❌ Don't try to fix all 5 bugs at once  
❌ Don't change agent logic or behavior  
❌ Don't add new tests (just verify existing ones work)  
❌ Don't commit anything else in this commit  
❌ Don't claim it's done until you've verified above  

---

## WHEN YOU'RE DONE

1. Reply: "Task 1 complete"
2. Paste the output of:
   - `python -c "from core.ollama_client import ChatOllama; print('✓ Import works')"`
   - `git log -1 --oneline` (to show your commit)
3. I will verify and approve

**Then we move to Task 2.**

---

## ESTIMATED TIME

- Reading this: 5 minutes
- Coding the fix: 10 minutes
- Testing: 10 minutes
- Committing: 5 minutes

**Total: 30 minutes**

---

**Start now. Reply when done.**
