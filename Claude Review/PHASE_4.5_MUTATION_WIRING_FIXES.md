# PHASE 4.5: Fix Incomplete Mutation Wiring

**To**: Kilo Code  
**Status**: Phase 4 mutations incomplete - need fixes  
**Objective**: Make mutations actually change agent behavior  
**Total time**: ~1.5 hours  

---

## CRITICAL FIRST STEP

**Before starting ANY task:**

1. Read TODO.md
2. Read session_log.md
3. **CRITICAL: Read and understand the mutation audit**
   - File: `MUTATION_AUDIT_REAL_OR_HALLUCINATED.md`
   - Why: Explains what's broken
   - Time: 5 minutes

---

## THE PROBLEM (In One Sentence)

**Mutations are proposed but never actually make agents change behavior because:**
1. Config parameters don't match agent code
2. Agents only load config at startup, not mid-session
3. Mutations never reach "approved/implemented" status in production

---

## THE SOLUTION (3 Tasks)

### TASK 17: Fix Mutation Parameters (Use Real Agent Variables)

**File**: `core/evolution.py`  
**Problem**: Mutations propose `exploration_factor` which doesn't exist in agent code  
**Time**: 20 minutes  

#### Step 1: Find what parameters agents ACTUALLY use (5 min)

Run this:
```bash
grep -n "temperature\|strategy\|depth\|confidence" agents/autobot.py agents/alpha_evaluator.py agents/beta_worker.py
```

**You'll find real parameters like:**
- `temperature` (LLM sampling)
- `system_prompt` (agent instructions)
- `evaluation_depth` (how thorough)
- `confidence_threshold` (when to act)

#### Step 2: Update propose_mutation() to use REAL parameters (10 min)

In `core/evolution.py`, find `propose_mutation()`:

**CURRENT (WRONG)**:
```python
def propose_mutation(agent_name, description, rationale, proposed_changes, expected_improvement, risk_level):
    # proposed_changes might be: {"exploration_factor": 0.2}
    # ^ This doesn't exist in agent code
```

**NEW (CORRECT)**:
```python
def propose_mutation(agent_name, description, rationale, proposed_changes, expected_improvement, risk_level):
    """Propose a mutation using REAL agent parameters."""
    
    # Validate that proposed_changes keys exist in agent code
    VALID_PARAMS = {
        "autobot": ["temperature", "system_prompt", "max_retries"],
        "alpha_evaluator": ["temperature", "evaluation_depth", "confidence_threshold"],
        "beta_worker": ["temperature", "system_prompt", "error_handling_mode"]
    }
    
    valid_keys = VALID_PARAMS.get(agent_name, [])
    for key in proposed_changes.keys():
        if key not in valid_keys:
            raise ValueError(f"Unknown parameter '{key}' for {agent_name}. Valid: {valid_keys}")
    
    # Rest of function continues...
```

#### Step 3: Test parameter validation (5 min)

```bash
python -c "
from core.evolution import propose_mutation, MutationType

# This should FAIL (parameter doesn't exist)
try:
    propose_mutation(
        agent_name='beta_worker',
        mutation_type=MutationType.STRATEGY_EVOLUTION,
        description='Test',
        rationale='Test',
        proposed_changes={'exploration_factor': 0.2},  # ← FAKE
        expected_improvement=0.1,
        risk_level='medium'
    )
    print('✗ FAILED: Should have rejected fake parameter')
except ValueError as e:
    print(f'✓ PASSED: Rejected fake parameter: {e}')

# This should PASS (parameter exists)
try:
    propose_mutation(
        agent_name='beta_worker',
        mutation_type=MutationType.STRATEGY_EVOLUTION,
        description='Test',
        rationale='Test',
        proposed_changes={'temperature': 0.5},  # ← REAL
        expected_improvement=0.1,
        risk_level='medium'
    )
    print('✓ PASSED: Accepted real parameter')
except ValueError as e:
    print(f'✗ FAILED: Should have accepted real parameter: {e}')
"
```

**Acceptance Criteria**:
- ✅ Fake parameters rejected (exploration_factor)
- ✅ Real parameters accepted (temperature, system_prompt, etc)

---

### TASK 18: Make Agents Reload Config Mid-Session

**File**: `agents/autobot.py`, `agents/alpha_evaluator.py`, `agents/beta_worker.py`  
**Problem**: Agents load config at startup, never reload during operation  
**Time**: 30 minutes  

#### Step 1: Understand current config loading (5 min)

Current code in `agents/autobot.py`:

```python
def __init__(self):
    from core.agent_config import get_config_store
    self.config_store = get_config_store()
    
    # Load config ONCE at startup
    self.config = self.config_store.get_active("autobot")
    self.temperature = self.config.get("temperature", 0.2)
    self.system_prompt = self.config.get("system_prompt", "...")
```

**Problem**: After this init, config never changes again.

#### Step 2: Add dynamic config reloading (20 min)

**IN EACH AGENT** (autobot.py, alpha_evaluator.py, beta_worker.py):

Replace the hardcoded config with a method:

```python
class AutobotAgent:
    def __init__(self):
        from core.agent_config import get_config_store
        self.config_store = get_config_store()
        self._load_active_config()  # Load once at startup
    
    def _load_active_config(self):
        """Load current active config (called at startup and before each decision)."""
        self.config = self.config_store.get_active("autobot")
        self.temperature = self.config.get("temperature", 0.2)
        self.system_prompt = self.config.get("system_prompt", "...")
        self.max_retries = self.config.get("max_retries", 3)
        # Add any other config parameters
    
    async def decide(self, state, goal):
        """Make a decision (called every loop cycle)."""
        
        # CRITICAL: Reload config before each decision
        self._load_active_config()  # ← THIS IS NEW
        
        # Now use the freshly-loaded config
        llm = ChatOllama(
            model="...",
            temperature=self.temperature  # Uses latest config
        )
        
        # Rest of decide() logic continues...
```

**Do this for all 3 agents:**
- `agents/autobot.py`: Add `_load_active_config()` + call it in `decide()`
- `agents/alpha_evaluator.py`: Same pattern
- `agents/beta_worker.py`: Same pattern

#### Step 3: Test config reloading (5 min)

```bash
python -c "
from core.agent_config import get_config_store
from agents.autobot import autobot_agent
import asyncio

async def test():
    store = get_config_store()
    
    # Get initial config
    config_v1 = store.get_active('autobot')
    temp_v1 = config_v1.get('temperature', 0.2)
    print(f'Initial temperature: {temp_v1}')
    
    # Simulate mutation: change config
    new_config = store.create_version(
        agent_name='autobot',
        changes={'temperature': 0.8},
        parent_version=config_v1.get('version', 'v1.0.0')
    )
    store.promote('autobot', new_config)
    print(f'Created new config version with temperature: 0.8')
    
    # Call agent decide (should now use new config)
    await autobot_agent.decide({'test': True}, None)
    
    # Check if agent loaded new config
    if autobot_agent.temperature == 0.8:
        print(f'✓ PASSED: Agent loaded new config (temperature={autobot_agent.temperature})')
    else:
        print(f'✗ FAILED: Agent still using old config (temperature={autobot_agent.temperature})')

asyncio.run(test())
"
```

**Acceptance Criteria**:
- ✅ All 3 agents have `_load_active_config()` method
- ✅ Config is reloaded before each `decide()` call
- ✅ Test shows config changes take effect mid-session

---

### TASK 19: Wire Mutation Approval to Real Implementation

**File**: `core/evolution.py` + `governance/consensus.py`  
**Problem**: Mutations proposed but never approved/implemented in production  
**Time**: 25 minutes  

#### Step 1: Add approval tracking (10 min)

In `core/evolution.py`, find `approve_mutation()`:

**CURRENT**:
```python
def approve_mutation(self, mutation_id: str, approved_by: str) -> bool:
    mutation = self.mutations[mutation_id]
    mutation.status = MutationStatus.APPROVED  # ← Just changes status
    # Doesn't actually implement!
    return True
```

**NEW**:
```python
def approve_mutation(self, mutation_id: str, approved_by: str) -> bool:
    """Approve a mutation AND automatically implement it."""
    
    if mutation_id not in self.mutations:
        return False
    
    mutation = self.mutations[mutation_id]
    
    # Mark as approved
    mutation.status = MutationStatus.APPROVED
    mutation.approved_by = approved_by
    mutation.approval_timestamp = datetime.utcnow().isoformat()
    self._save_mutation(mutation)
    
    # CRITICAL: Automatically implement it
    result = self.implement_mutation(mutation_id)
    
    if result["success"]:
        print(f"[EVOLUTION] Mutation {mutation_id} approved AND implemented")
        return True
    else:
        print(f"[EVOLUTION] Mutation {mutation_id} approved but implementation FAILED: {result['error']}")
        mutation.status = MutationStatus.FAILED
        self._save_mutation(mutation)
        return False
```

#### Step 2: Update consensus voting (10 min)

In `governance/consensus.py`, find where mutations are approved:

```python
# OLD:
if all(vote == "approve" for vote in votes):
    approve_mutation(mutation_id)  # Just changes status

# NEW:
if all(vote == "approve" for vote in votes):
    result = approve_mutation(mutation_id, approved_by="council")
    if result:
        print(f"✓ Mutation {mutation_id} implemented by council consensus")
    else:
        print(f"✗ Mutation {mutation_id} approved but failed to implement")
```

#### Step 3: Test mutation approval → implementation cycle (5 min)

```bash
python -c "
from core.evolution import propose_mutation, approve_mutation, implement_mutation, MutationType
import tempfile
import json

# Create a test mutation
mutation = propose_mutation(
    agent_name='autobot',
    mutation_type=MutationType.STRATEGY_EVOLUTION,
    description='Test config change',
    rationale='Testing approval workflow',
    proposed_changes={'temperature': 0.7},
    expected_improvement=0.1,
    risk_level='low'
)

print(f'1. Proposed mutation: {mutation.mutation_id}')
print(f'   Status: {mutation.status.value}')

# Approve it
result = approve_mutation(mutation.mutation_id, approved_by='test_user')
print(f'2. Approved mutation')
print(f'   Result: {result}')

# Check status
from core.evolution import get_evolution_engine
engine = get_evolution_engine()
updated_mutation = engine.mutations[mutation.mutation_id]
print(f'3. Final status: {updated_mutation.status.value}')

if updated_mutation.status.value == 'implemented':
    print('✓ PASSED: Mutation went from proposed → approved → implemented')
else:
    print(f'✗ FAILED: Mutation still in {updated_mutation.status.value} status')
"
```

**Acceptance Criteria**:
- ✅ Approve automatically calls implement
- ✅ Mutations reach "implemented" status
- ✅ Config is promoted to agents
- ✅ Test shows full cycle: propose → approve → implement

---

## HOW TO COMMIT

After each task:

```bash
git add .
git commit -m "Task X: [Description]

Problem: [What was wrong]
Solution: [What you fixed]
Files changed: [list]
Verification: [test output]"

git push
```

Reply with commit SHA.

---

## VERIFICATION CHECKLIST

After ALL THREE TASKS complete:

```bash
# 1. Mutation parameters are validated
grep -A 10 "VALID_PARAMS" core/evolution.py
# Should show real parameter names

# 2. Agents reload config mid-session
grep -n "_load_active_config" agents/*.py
# Should show it's called in decide() methods

# 3. Mutations reach implemented status
ls evolution/mutations/*.json | xargs grep '"status": "implemented"'
# Should show implemented mutations

# 4. Config actually changes agent behavior
python test_mutation_cycle.py
# Should show: temperature changed, agent uses new value
```

---

## TIMELINE

| Task | Time | What |
|------|------|------|
| **17** | 20 min | Fix mutation parameters (use real agent vars) |
| **18** | 30 min | Make agents reload config mid-session |
| **19** | 25 min | Wire approval → implementation |

**Total**: ~75 minutes = **1.25 hours**

**Result**: Mutations actually change agent behavior

---

## SUCCESS CRITERIA

After Phase 4.5 tasks complete:

```
Mutation proposed
    ↓ (based on real performance)
Mutation evaluated
    ↓ (against real agent parameters)
Mutation approved by council
    ↓ (auto-triggers implementation)
Config updated with new parameters
    ↓ (saved to config store)
Agents reload config mid-session
    ↓ (before each decision)
Agent behavior ACTUALLY CHANGES
    ↓
New performance measured in next cycle
    ↓ (Feedback loop closes)
✓ AUTONOMOUS EVOLUTION WORKS
```

---

## CRITICAL REMINDERS

1. **Read TODO.md + session_log FIRST** (before starting)
2. **Read MUTATION_AUDIT_REAL_OR_HALLUCINATED.md** (understand the problem)
3. **Test each task locally** (must pass verification)
4. **Commit + push after EACH task** (git proof required)
5. **Reply with commit SHA** (how Martin verifies)

---

**Ready to start Phase 4.5?**

Start Task 17.

