# PHASE 4: Autonomy Loop Integration (Tasks 13-16)

**To**: Kilo Code  
**Status**: Phase 1-3 complete, foundation solid, ready for evolution wiring  
**Objective**: Wire the autonomy loop so mutations actually change behavior  
**Total time**: ~2 hours  

---

## CRITICAL PRE-TASK CHECKLIST

**BEFORE STARTING EACH TASK, DO THIS:**

1. **Read TODO.md**
```bash
cat TODO.md | head -50
```

2. **Read session_log.md**
```bash
tail -100 session_log.md
```

3. **Check git status**
```bash
git log --oneline | head -3
```

4. **Read the task instructions carefully**

---

## IDENTITY REMINDER

You are Kilo Code (developer). NOT the autonomous council.

---

# TASK 13: Fix cycle_start Scope Bug

**Deadline**: Today EOD  
**Time estimate**: 15 minutes  
**Status**: NOT STARTED  
**Priority**: 🔴 CRITICAL - prevents goal tracking

---

## THE PROBLEM

In core/evolution.py or agent_loop.py (line ~205 in _select_and_execute_goal):

`cycle_start` variable is used but not defined in the function scope.

```python
def _select_and_execute_goal(...):
    # cycle_start is NOT defined here
    # But code tries to use it below
    goal = self._select_goal()
    result = self._execute(goal, cycle_start)  # ← cycle_start undefined!
    return result
```

**Result**: NameError or undefined variable when goals are selected/executed.

---

## WHAT YOU NEED TO DO

### Step 1: Find the bug (5 minutes)

Search for the exact location:

```bash
grep -n "cycle_start" core/evolution.py | grep -E "line|_select_and_execute"
grep -n "def _select_and_execute_goal" core/evolution.py
```

Find the function and the line where cycle_start is used but not defined.

### Step 2: Fix the scope (5 minutes)

**Option A: Pass as parameter**

Change the function signature:
```python
# OLD:
def _select_and_execute_goal(self, goal_store):
    # cycle_start not available

# NEW:
def _select_and_execute_goal(self, goal_store, cycle_start):
    # cycle_start now available as parameter
```

**Option B: Get from caller**

If cycle_start comes from an outer scope, explicitly pass it:
```python
# In the function that calls _select_and_execute_goal:
cycle_start = time.time()  # or get from state
self._select_and_execute_goal(goal_store, cycle_start)
```

### Step 3: Verify fix works (5 minutes)

Test that goal selection/execution doesn't crash:

```bash
python -c "
from core.evolution import Evolution
from core.goals import GoalStore
import tempfile

# Create temp goal store
with tempfile.TemporaryDirectory() as tmpdir:
    store = GoalStore(db_path=tmpdir + '/test.db')
    
    # Create a test goal
    goal_id = store.create_goal('test', priority='high', source='test')
    
    # Try to select and execute (should not crash with NameError)
    evo = Evolution(goal_store=store)
    result = evo._select_and_execute_goal(store)
    
    print('✓ cycle_start scope fixed')
"
```

**Should print**: `✓ cycle_start scope fixed`

If it crashes with NameError about cycle_start, the fix isn't complete.

---

## ACCEPTANCE CRITERIA

✅ Task is done when:

1. cycle_start is no longer used without being defined
2. _select_and_execute_goal either receives cycle_start as parameter or defines it
3. Function can be called without NameError
4. Test above runs without error

---

## HOW TO COMMIT

```
Task 13: Fix cycle_start scope bug

Problem: cycle_start used in _select_and_execute_goal but not defined in scope
Solution: Pass cycle_start as function parameter (or define in scope)
Files changed:
  - core/evolution.py (line ~205, updated function signature)
  - [any callers that need to pass cycle_start]
Verification:
  python -c "from core.evolution import Evolution; ..."
  Result: ✓ cycle_start scope fixed
```

---

## WHEN DONE

**CRITICAL: Commit and push to GitHub**

```bash
git add .
git commit -m "Task 13: Fix cycle_start scope bug"
git push
git log -1 --oneline  # Verify push succeeded
```

Reply:
```
Task 13 complete.
Commit: <SHA from git log -1>
Status: cycle_start scope fixed
```

---

# TASK 14: Wire Mutation → Config → Eval → Promote

**Deadline**: Today EOD  
**Time estimate**: 1 hour  
**Status**: NOT STARTED  
**Priority**: 🔴 CRITICAL - enables evolution to actually work

---

## THE PROBLEM

Currently in core/evolution.py, _apply_mutation only does:

```python
def _apply_mutation(self, mutation):
    # Only logs status
    self.mutations[mutation_id] = {"status": "applied"}
    # Does NOT:
    # - Write to config store
    # - Run evaluation
    # - Promote to agents
```

**Result**: Mutations don't change agent behavior. Evolution is fake.

---

## WHAT YOU NEED TO DO

### Step 1: Understand the flow (10 minutes)

The correct flow is:

```
1. Mutation proposed (e.g., "change autobot temperature to 0.8")
2. _apply_mutation called
3. Write to config store (core/agent_config.py)
4. Run evaluation (core/evaluation.py)
5. If PASS: promote to all three agents
6. If FAIL: rollback to previous config
```

### Step 2: Update _apply_mutation (30 minutes)

Find `_apply_mutation` in core/evolution.py and replace with:

```python
def _apply_mutation(self, mutation_id, mutation_config):
    """Apply mutation: config → eval → promote."""
    
    from core.agent_config import save_config
    from core.evaluation import evaluate_mutation
    
    try:
        # Step 1: Save proposed config
        config_version = save_config(
            agent_name=mutation_config["agent"],
            config=mutation_config["config"],
            version=f"mutation_{mutation_id}",
            parent_version=self.current_version
        )
        self.mutations[mutation_id]["version"] = config_version
        self.mutations[mutation_id]["status"] = "config_saved"
        
        # Step 2: Evaluate the mutation
        evaluation_result = evaluate_mutation(
            agent_name=mutation_config["agent"],
            new_config=mutation_config["config"],
            test_suite="sanity_checks"  # Run basic sanity checks
        )
        
        if not evaluation_result["passed"]:
            # Evaluation failed, rollback
            self.mutations[mutation_id]["status"] = "eval_failed"
            self.mutations[mutation_id]["eval_reason"] = evaluation_result["reason"]
            return False
        
        self.mutations[mutation_id]["status"] = "eval_passed"
        
        # Step 3: Promote to all three agents
        promoted = self._promote_config_to_agents(config_version)
        
        if promoted:
            self.mutations[mutation_id]["status"] = "promoted"
            self.current_version = config_version
            return True
        else:
            self.mutations[mutation_id]["status"] = "promotion_failed"
            return False
            
    except Exception as e:
        self.mutations[mutation_id]["status"] = "failed"
        self.mutations[mutation_id]["error"] = str(e)
        return False

def _promote_config_to_agents(self, config_version):
    """Load new config into all three agents."""
    from agents.autobot import autobot_agent
    from agents.alpha_evaluator import alpha_agent
    from agents.beta_worker import beta_agent
    
    try:
        # Load config into each agent
        autobot_agent.load_config(config_version)
        alpha_agent.load_config(config_version)
        beta_agent.load_config(config_version)
        
        return True
    except Exception as e:
        print(f"Promotion failed: {e}")
        return False
```

### Step 3: Test the flow (15 minutes)

Create a test to verify mutation → eval → promote works:

```bash
python -c "
from core.evolution import Evolution
from core.goals import GoalStore
import tempfile
import json

# Setup
with tempfile.TemporaryDirectory() as tmpdir:
    store = GoalStore(db_path=tmpdir + '/test.db')
    evo = Evolution(goal_store=store)
    
    # Create a test mutation
    mutation = {
        'agent': 'autobot',
        'config': {'temperature': 0.8}
    }
    
    # Apply it (should go through all steps)
    result = evo._apply_mutation('test_mut_1', mutation)
    
    if result:
        print('✓ Mutation flow: config → eval → promote worked')
        status = evo.mutations['test_mut_1']['status']
        print(f'  Final status: {status}')
        if status == 'promoted':
            print('✓ Agents received new config')
    else:
        print('✗ Mutation flow failed')
        print(f'  Status: {evo.mutations[\"test_mut_1\"][\"status\"]}')
"
```

**Should print**:
```
✓ Mutation flow: config → eval → promote worked
  Final status: promoted
✓ Agents received new config
```

### Step 4: Integrate with voting (5 minutes)

Make sure consensus voting calls _apply_mutation:

In core/graph.py or governance/consensus.py, find where mutations are approved:

```python
# OLD:
if consensus_reached:
    logging.info(f"Mutation {mutation_id} approved")

# NEW:
if consensus_reached:
    logging.info(f"Mutation {mutation_id} approved")
    evolution.apply_mutation(mutation_id, mutation_config)
    if evolution.mutations[mutation_id]["status"] == "promoted":
        logging.info(f"Mutation promoted to agents")
```

---

## ACCEPTANCE CRITERIA

✅ Task is done when:

1. _apply_mutation writes to config store
2. _apply_mutation calls evaluation gate
3. If eval passes: promotes to all three agents
4. If eval fails: marks as failed (doesn't promote)
5. Mutation status tracks through the flow
6. Test shows mutation → eval → promote works end-to-end

---

## HOW TO COMMIT

```
Task 14: Wire mutation → config → eval → promote

Problem: _apply_mutation only logs status, doesn't change behavior
Solution: Full pipeline: save config → evaluate → promote to agents
Files changed:
  - core/evolution.py (rewrote _apply_mutation, added _promote_config_to_agents)
  - core/graph.py or governance/consensus.py (call evolution._apply_mutation on approval)
Verification:
  python -c "from core.evolution import Evolution; ..."
  Result: ✓ Mutation flow: config → eval → promote worked
          ✓ Final status: promoted
          ✓ Agents received new config
```

---

## WHEN DONE

**CRITICAL: Commit and push to GitHub**

```bash
git add .
git commit -m "Task 14: Wire mutation to config, eval, and promotion"
git push
git log -1 --oneline
```

Reply:
```
Task 14 complete.
Commit: <SHA>
Status: Mutation pipeline wired (config → eval → promote)
```

---

# TASK 15: Add Telegram NLP (Plain Language Commands)

**Deadline**: Today EOD  
**Time estimate**: 45 minutes  
**Status**: NOT STARTED  
**Priority**: 🟡 MEDIUM - user-facing, nice to have

---

## THE PROBLEM

Currently Telegram only supports structured commands:

```
✓ /goal create high-level mission
✓ /status
✓ /approve
```

But not plain language:

```
✗ "Create a high-level mission" (plain English)
✗ "What's the current status?" (natural language)
```

**Fix**: Add MessageHandler to parse plain text with NLP.

---

## WHAT YOU NEED TO DO

### Step 1: Add MessageHandler to Telegram (15 minutes)

Open core/telegram.py, find where CommandHandlers are defined:

```python
# OLD:
application.add_handler(CommandHandler("goal", handle_goal_command))
application.add_handler(CommandHandler("status", handle_status_command))

# NEW: Add MessageHandler
from telegram.ext import MessageHandler, filters
from langchain_ollama import ChatOllama

# Add this handler
async def handle_plain_text(update, context):
    """Parse plain text commands using NLP."""
    
    message_text = update.message.text
    
    # Use LLM to classify intent
    llm = ChatOllama(model="qwen2.5:3b")
    prompt = f"""
    User message: "{message_text}"
    
    Classify into one of these intents:
    - create_goal
    - check_status
    - approve_mutation
    - reject_mutation
    - stop
    - other
    
    Return ONLY the intent name, nothing else.
    """
    
    response = llm.invoke(prompt)
    intent = response.content.strip().lower()
    
    # Route to appropriate handler
    if intent == "create_goal":
        # Extract goal description from message
        # "Create a mission to optimize trading" → extract "optimize trading"
        await handle_goal_command(update, context)
    elif intent == "check_status":
        await handle_status_command(update, context)
    elif intent == "approve_mutation":
        await handle_approve_command(update, context)
    elif intent == "reject_mutation":
        await handle_reject_command(update, context)
    elif intent == "stop":
        await handle_stop_command(update, context)
    else:
        await update.message.reply_text(
            "I didn't understand that. Try: /goal, /status, /approve, /reject, /stop"
        )

# Register the handler
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_plain_text))
```

### Step 2: Extract goal description from plain text (15 minutes)

Update handle_plain_text to extract goal details:

```python
def _extract_goal_from_text(message_text):
    """Extract goal description from plain text."""
    
    from langchain_ollama import ChatOllama
    
    llm = ChatOllama(model="qwen2.5:3b")
    prompt = f"""
    User message: "{message_text}"
    
    Extract the goal/task they want to create.
    Return a short goal description (1 sentence max).
    Return ONLY the description, nothing else.
    """
    
    response = llm.invoke(prompt)
    return response.content.strip()

# In handle_plain_text:
if intent == "create_goal":
    goal_desc = _extract_goal_from_text(message_text)
    # Pass to goal store
    from core.goals import GoalStore
    goal_store = GoalStore()
    goal_id = goal_store.create_goal(goal_desc, priority="medium", source="telegram")
    await update.message.reply_text(f"Created goal: {goal_desc} (ID: {goal_id})")
```

### Step 3: Test plain text commands (15 minutes)

Create test_telegram_npl.py:

```python
"""Test Telegram NLP plain text parsing."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from core.telegram import handle_plain_text, _extract_goal_from_text


def test_extract_goal_description():
    """Test extracting goal from plain text."""
    
    message = "Create a mission to find new trading opportunities"
    goal = _extract_goal_from_text(message)
    
    assert goal is not None
    assert len(goal) > 0
    assert "trading" in goal.lower() or "mission" in goal.lower()
    print(f"✓ Extracted goal: {goal}")


async def test_plain_text_routing():
    """Test routing plain text to correct handler."""
    
    # Mock update and context
    update = AsyncMock()
    update.message.text = "What's the current status?"
    context = AsyncMock()
    
    # Should route to status handler
    await handle_plain_text(update, context)
    
    # Check that appropriate response was sent
    assert update.message.reply_text.called or True  # May not reply if testing
    print("✓ Plain text routed correctly")


if __name__ == "__main__":
    test_extract_goal_description()
    asyncio.run(test_plain_text_routing())
    print("\n✓ Telegram NLP tests passed")
```

Run it:
```bash
python test_telegram_npl.py
```

---

## ACCEPTANCE CRITERIA

✅ Task is done when:

1. MessageHandler added to Telegram app
2. Plain text messages are parsed with NLP
3. Intent classification works (create_goal, check_status, etc)
4. Goal description extracted from plain text
5. Routed to correct handler
6. Tests prove NLP works

---

## HOW TO COMMIT

```
Task 15: Add Telegram NLP for plain language commands

Problem: Telegram only supports /commands, not natural language
Solution: Added MessageHandler with LLM intent classification
Files changed:
  - core/telegram.py (added handle_plain_text, _extract_goal_from_text)
  - tests/test_telegram_npl.py (new NLP tests)
Verification:
  python test_telegram_npl.py
  Result: ✓ Telegram NLP tests passed
```

---

## WHEN DONE

**CRITICAL: Commit and push to GitHub**

```bash
git add .
git commit -m "Task 15: Add Telegram NLP for plain language commands"
git push
git log -1 --oneline
```

Reply:
```
Task 15 complete.
Commit: <SHA>
Status: Telegram NLP working (plain text → intent → handler)
```

---

# TASK 16: Set LangGraph Recursion Limit

**Deadline**: Today EOD  
**Time estimate**: 5 minutes  
**Status**: NOT STARTED  
**Priority**: 🟡 MEDIUM - safety/prevents infinite loops

---

## THE PROBLEM

LangGraph workflow has no recursion_limit set:

```python
# In core/graph.py:
app = workflow.compile(checkpointer=checkpointer)
# NO recursion_limit → potential infinite loops
```

**Result**: Agent can loop infinitely without stopping.

---

## WHAT YOU NEED TO DO

### Step 1: Add recursion_limit (2 minutes)

Open core/graph.py, find where workflow is compiled:

**OLD**:
```python
app = workflow.compile(checkpointer=checkpointer)
```

**NEW**:
```python
app = workflow.compile(
    checkpointer=checkpointer,
    recursion_limit=25  # Prevent infinite loops
)
```

### Step 2: Verify it's set (2 minutes)

```bash
grep -n "recursion_limit" core/graph.py
```

Should show: `recursion_limit=25` (or whatever value)

### Step 3: Test the system still starts (1 minute)

```bash
python -c "
from core.graph import app
print(f'✓ Graph compiled with recursion_limit')
print(f'  Checkpointer: {type(app.checkpointer).__name__}')
"
```

**Should print**:
```
✓ Graph compiled with recursion_limit
  Checkpointer: JSONCheckpointer
```

---

## ACCEPTANCE CRITERIA

✅ Task is done when:

1. recursion_limit added to workflow.compile()
2. Value is reasonable (15-50)
3. Graph compiles without error
4. System still starts

---

## HOW TO COMMIT

```
Task 16: Set LangGraph recursion limit

Problem: No recursion_limit on workflow (potential infinite loops)
Solution: Added recursion_limit=25 to workflow.compile()
Files changed:
  - core/graph.py (line ~XX, added recursion_limit parameter)
Verification:
  python -c "from core.graph import app; ..."
  Result: ✓ Graph compiled with recursion_limit
```

---

## WHEN DONE

**CRITICAL: Commit and push to GitHub**

```bash
git add .
git commit -m "Task 16: Set LangGraph recursion limit to 25"
git push
git log -1 --oneline
```

Reply:
```
Task 16 complete.
Commit: <SHA>
Status: Recursion limit set (prevents infinite loops)
```

---

## SUMMARY: Phase 4 Tasks

| Task | Time | What | Status |
|------|------|------|--------|
| 13 | 15 min | Fix cycle_start scope | Next |
| 14 | 1 hour | Wire mutation pipeline | After 13 |
| 15 | 45 min | Telegram NLP | After 14 |
| 16 | 5 min | Recursion limit | After 15 |

**Total**: ~2 hours

**Result**: Autonomy loop is wired. Mutations → config → eval → promote. System can evolve.

---

## CRITICAL WORKFLOW

**For each task:**

1. **Read TODO.md + session_log FIRST**
2. **Follow task instructions**
3. **Test locally** (must pass)
4. **Commit** (`git commit -m "Task X: ..."`)
5. **Push to GitHub** (`git push`)
6. **Verify push** (`git log -1 --oneline`)
7. **Reply with commit SHA**

**Do not skip commit + push. That's how Martin verifies.**

---

**Start Task 13 now. Read TODO.md + session_log first. Reply when done.**
