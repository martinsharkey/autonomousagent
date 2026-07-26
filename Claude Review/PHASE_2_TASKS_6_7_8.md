# PHASE 2: Test Infrastructure + System Verification

**To**: Kilo Code  
**Status**: Phase 1 complete (5 bugs fixed), ready for Phase 2  
**Objective**: Get tests passing + verify system works  
**Total time**: ~3 hours  

---

## IDENTITY REMINDER

You are Kilo Code, a developer assistant. NOT the autonomous council.

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

# TASK 6: Set Up Test Mocking + Run Full Test Suite

**Deadline**: Today EOD  
**Time estimate**: 45 minutes  
**Status**: NOT STARTED  

---

## THE PROBLEM

Tests fail because:
1. Ollama models aren't installed in test environment
2. Tests try to load real ChatOllama (crashes)
3. No way to run tests without real models

**Result**: Can't verify system works via automated tests.

---

## WHAT YOU NEED TO DO

### Step 1: Create test fixture for mocking Ollama (10 minutes)

Create file: `tests/conftest.py`

```python
"""pytest configuration and fixtures."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_ollama():
    """Mock ChatOllama for tests."""
    with patch('core.ollama_client.ChatOllama') as mock_class:
        # Create a mock instance
        mock_instance = MagicMock()
        
        # When invoke() is called, return a mock response
        mock_response = MagicMock()
        mock_response.content = "test response from mocked model"
        mock_instance.invoke.return_value = mock_response
        
        # When the class is instantiated, return the mock instance
        mock_class.return_value = mock_instance
        
        yield mock_instance


@pytest.fixture
def mock_goals_store():
    """Mock goal store for tests."""
    mock_store = MagicMock()
    mock_store.create_goal.return_value = "goal_123"
    mock_store.get_status.return_value = {"status": "pending"}
    yield mock_store


@pytest.fixture
def mock_ollama_for_all_agents():
    """Patch ChatOllama for all agent imports."""
    with patch('core.ollama_client.ChatOllama') as mock_class:
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "mocked agent response"
        mock_instance.invoke.return_value = mock_response
        mock_class.return_value = mock_instance
        yield mock_instance
```

### Step 2: Update test imports (10 minutes)

In any test file that uses ChatOllama or agents, add at the top:

```python
import pytest
from unittest.mock import patch


@patch('core.ollama_client.ChatOllama')
def test_autobot_votes(mock_ollama):
    """Test autobot voting without real model."""
    # Your test here
    pass
```

Or use the fixture:

```python
def test_agent_with_mock(mock_ollama):
    """Test agent using mocked model."""
    # Your test here
    # mock_ollama will be used instead of real ChatOllama
    pass
```

### Step 3: Run full test suite (15 minutes)

```bash
pytest tests/ -v --tb=short 2>&1 | tee test_results.txt
```

**This will show:**
- How many tests pass
- How many fail
- What the failures are

Save the output to `test_results.txt` so we can see what's broken.

### Step 4: Count failures (10 minutes)

```bash
grep -E "^(PASSED|FAILED|ERROR)" test_results.txt | sort | uniq -c
```

This shows:
- Number of passed tests
- Number of failed tests
- Number of errored tests

**Example output:**
```
10 PASSED
5 FAILED
2 ERROR
```

---

## ACCEPTANCE CRITERIA

✅ Task is done when:

1. File `tests/conftest.py` exists with mock_ollama fixture
2. Full test suite runs without crashing
3. We have a count: X passed, Y failed, Z errors
4. You provide `test_results.txt` output

---

## HOW TO COMMIT

```
Task 6: Set up test infrastructure with Ollama mocking

Problem: Tests fail because ChatOllama requires real Ollama models
Solution: Added pytest fixtures in conftest.py to mock ChatOllama
Files changed:
  - tests/conftest.py (new: mock_ollama, mock_goals_store fixtures)
Verification:
  pytest tests/ -v
  Result: [X passed, Y failed, Z errors]
Test output: [paste key lines from results]
```

---

## WHEN DONE

Reply:
```
Task 6 complete.
Commit: <SHA>
Test results:
  Passed: X
  Failed: Y
  Errors: Z
```

Then wait for Task 7.

---

# TASK 7: Fix Test Failures Until 0 Failures

**Deadline**: Tomorrow EOD  
**Time estimate**: 1-1.5 hours  
**Status**: NOT STARTED  

---

## THE PROBLEM

After Task 6, we have X failing tests. Each one needs fixing.

**Your job**: Go through each failure and fix it.

---

## WHAT YOU NEED TO DO

### Step 1: Get detailed failure list (5 minutes)

```bash
pytest tests/ -v --tb=short 2>&1 | grep -E "^tests/.*FAILED" > failures.txt
cat failures.txt
```

This shows which tests failed and where.

### Step 2: For each failure, analyze and fix (30-60 minutes)

For example, if you see:
```
tests/test_autobot.py::test_agent_loads_model FAILED
```

Run just that test to see the error:
```bash
pytest tests/test_autobot.py::test_agent_loads_model -v --tb=long
```

**Common fixes:**

**Problem**: `FileNotFoundError` (still missing mkdir somewhere)
```bash
# Search for other write locations
grep -r "with open" --include="*.py" tests/
# Add mkdir before each one
```

**Problem**: `ImportError` (still importing ChatOllama wrong)
```bash
# Make sure all imports use:
from core.ollama_client import ChatOllama
# Not the old direct imports
```

**Problem**: `ModuleNotFoundError` (missing dependency)
```bash
pip install <module>
```

**Problem**: Test logic error (test is wrong, not code)
```bash
# Review the test
# Fix the test or the code to match
```

### Step 3: Run tests again (10 minutes)

After each fix:
```bash
pytest tests/ -v --tb=short
```

Check if failure count decreased.

### Step 4: Repeat until 0 failures (30-60 minutes)

Keep fixing until:
```
X passed, 0 failed, 0 errors
```

---

## ACCEPTANCE CRITERIA

✅ Task is done when:

1. `pytest tests/ -v` shows 0 failures and 0 errors
2. All tests that should pass DO pass
3. Tests that need Ollama use mocks (don't fail due to missing models)

---

## HOW TO COMMIT

```
Task 7: Fix test failures until 0 failures

Problem: 15 tests failing after Task 6
Solution: Fixed each failure:
  - Added mock patches in 4 tests
  - Fixed mkdir issue in 3 tests
  - Fixed import paths in 8 tests
Files changed:
  - tests/test_autobot.py (added mocks)
  - tests/test_evolution.py (fixed imports)
  - core/communication.py (fixed another mkdir)
  - [etc]
Verification:
  pytest tests/ -v
  Result: All X tests passed, 0 failed, 0 errors
```

---

## WHEN DONE

Reply:
```
Task 7 complete.
Commit: <SHA>
Test results: X tests passed, 0 failed, 0 errors
```

Then wait for Task 8.

---

# TASK 8: Verify System Works (Preflight + Health + Daemon)

**Deadline**: Tomorrow EOD  
**Time estimate**: 45 minutes  
**Status**: NOT STARTED  

---

## THE PROBLEM

Tests pass, but can the actual system run?

- Can it start without crashing?
- Are all systems healthy?
- Can the daemon run in the background?

---

## WHAT YOU NEED TO DO

### Step 1: Run preflight check (10 minutes)

```bash
python main.py --preflight
```

**Should output something like:**
```
✓ Ollama is running
✓ Model qwen2.5:3b is loaded
✓ System has 8GB RAM (required: 6GB)
✓ All preflight checks passed
Status: can_run = true
```

If it fails:
- Install Ollama (if not installed)
- Pull the required model: `ollama pull qwen2.5:3b`
- Check available RAM

### Step 2: Run health check (10 minutes)

```bash
python main.py --health
```

**Should output something like:**
```
=== SYSTEM HEALTH CHECK ===
Graphs: HEALTHY (checkpointer loaded)
Models: HEALTHY (3/3 models available)
Storage: HEALTHY (65% usage)
Audit log: HEALTHY (last entry: 2026-07-25 12:30:45)
Governance: HEALTHY (voting engine ready)
Overall: ALL SYSTEMS GREEN
```

If any show UNHEALTHY:
- Check the error message
- Fix what it says is broken

### Step 3: Start daemon (15 minutes)

```bash
timeout 30 python council_daemon.py --interval 10
```

**Should output:**
```
[12:30:45] Starting autonomous council daemon
[12:30:46] Loading agent configs
[12:30:47] Starting Telegram listener
[12:30:48] Cycle 1: Checking goals...
[12:30:49] Health check: OK
...
[12:31:15] Daemon shutting down gracefully
```

**Should NOT output:**
```
Error
Exception
Traceback
```

If it crashes:
- Note the error message
- Fix what caused the crash
- Run again

### Step 4: Verify daemon produced logs (5 minutes)

Check that daemon created log files:

```bash
ls -la *.log 2>/dev/null || echo "No logs yet (OK)"
```

Check that checkpointer created state file:

```bash
ls -la checkpoints.json 2>/dev/null || echo "No checkpoints yet (OK)"
```

Both are optional but good signs if they exist.

---

## ACCEPTANCE CRITERIA

✅ Task is done when:

1. `python main.py --preflight` shows `can_run = true`
2. `python main.py --health` shows all systems HEALTHY
3. `python council_daemon.py --interval 10` runs for 30 seconds without crashing
4. No exceptions or errors in output

---

## HOW TO COMMIT

```
Task 8: Verify system works (preflight + health + daemon)

Problem: Need to prove system can actually run
Solution: Tested all three startup paths
Files changed: (none, just verification)
Verification:
  1. python main.py --preflight
     Result: ✓ can_run = true
  2. python main.py --health
     Result: ✓ ALL SYSTEMS GREEN
  3. timeout 30 python council_daemon.py --interval 10
     Result: ✓ Ran 30 seconds without error
```

---

## WHEN DONE

Reply:
```
Task 8 complete.
Commit: <SHA> (if any code changes)
Verification results:
  - Preflight: ✓ can_run = true
  - Health: ✓ all green
  - Daemon: ✓ ran 30s without error
```

---

## SUMMARY: Phase 2 Tasks

| Task | Time | Goal |
|------|------|------|
| 6: Mock Ollama + run tests | 45 min | See what tests fail |
| 7: Fix test failures | 1-1.5 hr | Get to 0 failures |
| 8: Verify system | 45 min | Prove it actually runs |

**Total**: ~3 hours

**Result**: Clean tests + working system

---

## WHAT COMES NEXT (After Phase 2)

Once you're done with Phase 2:
- Tests pass (0 failures)
- System starts without crashing
- All health checks green

Then we can move to **Phase 3: Autonomy Integration**

That's when things get interesting (goals, mutations, learning).

---

## IMPORTANT

1. **Do tasks in order**: 6 → 7 → 8
2. **Finish one before starting next**
3. **No [COUNCIL:*] prefixes** - you're the developer
4. **Reply with proof** - test numbers, commit SHA
5. **If stuck**: Tell me what's failing, I'll help debug

---

**Start Task 6 now. Reply when done.**
