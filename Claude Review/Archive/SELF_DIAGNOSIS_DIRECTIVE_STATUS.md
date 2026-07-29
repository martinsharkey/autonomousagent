# 🚨 SELF-DIAGNOSIS DIRECTIVE - IMPLEMENTATION STATUS

**Directive Source**: NotebookLM suggestion to Kilo  
**Objective**: Allow agents to read error logs and self-correct when mutations fail  
**Status**: PARTIALLY IMPLEMENTED - Critical gaps remain  

---

## DIRECTIVE REQUIREMENTS vs ACTUAL IMPLEMENTATION

### Requirement 1: `error_feedback` Field in AgentState
**Directive**: "Extend the `AgentState` schema to include an `error_feedback` field"

**Implementation Status**: ❌ **NOT IMPLEMENTED**

```python
# Current AgentState (core/state.py):
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    loop_count: int
    recent_tool_invocations: Annotated[list[str], operator.add]
    completed_nodes: Annotated[list[str], operator.add]
    codebase_hash: str
    # ... other fields ...
    # ❌ NO error_feedback field
```

**What's Missing**:
```python
# Should be:
error_feedback: Optional[str] = None  # Stack trace/error info
error_trace: Optional[Dict] = None    # Full exception details
```

**Impact**: Agents cannot receive error information even if it's captured.

---

### Requirement 2: LangGraph Error Handlers
**Directive**: "LangGraph provides an `error_handler` primitive that fires specifically after a node exhausts its retries"

**Implementation Status**: ⚠️ **PARTIALLY IMPLEMENTED**

**What exists** (core/rollback.py):
```python
def error_handler_node(state: AgentState) -> Dict[str, Any]:
    """Handle errors when loop_count >= 5"""
    if state["loop_count"] >= 5:
        return {"messages": [...]}
    # Attempts rollback to checkpoint
```

**What's WRONG**:
1. ❌ `error_handler_node` is added as a **regular node**, not as LangGraph's native error handler
2. ❌ Not attached to tool execution nodes via `@node.error_handler` decorator
3. ❌ Won't fire when tools actually fail with exceptions
4. ❌ Exception details never captured into state

**How it should work**:
```python
# What directive requires (NOT implemented):
from langgraph.graph import add_node_error_handler

@add_node_error_handler
def handle_tool_error(state: AgentState, error: Exception) -> Dict:
    """Fires when a tool node throws exception"""
    return {
        "error_feedback": str(error),  # Inject stack trace
        "error_trace": traceback.format_exc()
    }

# Then attach to nodes:
workflow.add_node("execute_mutation", execute_mutation_node)
workflow.set_error_handler(["execute_mutation", "test_mutation"], handle_tool_error)
```

**Current implementation**: ❌ MISSING

---

### Requirement 3: Circuit Breaker in Conditional Edge
**Directive**: "Place the `loop_count >= 3` safety check inside the conditional edge function"

**Implementation Status**: ⚠️ **PARTIALLY IMPLEMENTED**

**What exists** (core/graph.py):
```python
def deterministic_router(state: AgentState) -> str:
    if state["loop_count"] >= 5:  # ⚠️ Should be >= 3
        print(f"[SYSTEM OVERRIDE] TTL limit {state['loop_count']} breached. Terminating.")
        return "terminal_fallback"
    # ... routing logic ...
```

**Issues**:
1. ✓ Conditional edge is used (correct placement)
2. ✓ loop_count checked
3. ❌ Threshold is 5, directive says 3
4. ❌ Should route to `compensate` node, not `terminal_fallback`

**Correct implementation should be**:
```python
def deterministic_router(state: AgentState) -> str:
    if state["loop_count"] >= 3:  # Directive says 3 loops max
        print(f"[SYSTEM] Loop limit reached. Routing to compensate.")
        return "compensate"  # SAGA rollback, not terminal
    # ... rest of routing ...
```

---

### Requirement 4: SAGA Pattern Rollback
**Directive**: "The compensate node must execute SAGA pattern rollback...restore to last verified codebase_hash"

**Implementation Status**: ⚠️ **PARTIALLY IMPLEMENTED**

**What exists** (core/rollback.py):
```python
def error_handler_node(state: AgentState) -> Dict[str, Any]:
    if state["loop_count"] >= 5:
        # Looks for checkpoints
        if os.path.exists(ROLLBACK_DIR):
            for filename in os.listdir(ROLLBACK_DIR):
                if filename.endswith(".json"):
                    checkpoints.append(filename)
        # Calls rollback_to_checkpoint
```

**Issues**:
1. ✓ Checkpoints exist
2. ✓ rollback_to_checkpoint called
3. ❌ No explicit `compensate` node (just error_handler_node)
4. ❌ Not reached via conditional edge route (no `compensate` routing)
5. ❌ No explicit SAGA pattern state machine (transactions not tracked)

**Missing SAGA tracking**:
```python
# Should track in state:
saga_transactions: List[Dict] = []  # What was changed, in what order
saga_compensation_plan: List[Dict] = []  # How to undo each change

# When applying mutations:
saga_transactions.append({
    "mutation_id": mutation_id,
    "files_changed": [...],
    "codebase_hash_before": codebase_hash,
    "codebase_hash_after": new_hash
})

# On rollback:
for transaction in reversed(saga_transactions):
    restore_files(transaction["files_changed"], transaction["codebase_hash_before"])
```

---

### Requirement 5: Updated Agent Prompts for Self-Correction
**Directive**: "Update system prompts so they actively look for the `error_feedback` variable"

**Implementation Status**: ❌ **NOT IMPLEMENTED**

**Current alpha_evaluator prompt**:
```python
prompt = f"""
You are Alpha, the mission alignment evaluator for the autonomous council.

Evaluate this code mutation on two criteria:

1. MISSION ALIGNMENT: Does this mutation serve the core mission?
2. TEST READINESS: Is this mutation ready for testing?

CORE MISSION: Autonomous 3-agent council...
MUTATION RATIONALE: {mission_rationale}
...
"""
```

**What's MISSING**:
```python
# Should include:
if state.get("error_feedback"):
    prompt += f"""
    
    ⚠️ PREVIOUS MUTATION FAILED:
    Error: {state["error_feedback"]}
    
    SELF-CORRECTION TASK:
    1. Analyze the stack trace above
    2. Identify why the mutation failed
    3. Propose a revised mutation that fixes the error
    4. Output your revised code mutation
    """
```

**Impact**: Even if error_feedback was captured, agents wouldn't know to use it.

---

### Requirement 6: Workflow Logging & Telegram Notification
**Directive**: "Update session_log.md and send Telegram notification"

**Implementation Status**: ❌ **NOT IMPLEMENTED**

**No commits about**:
- Self-diagnosis upgrade
- Error handler injection
- SAGA pattern rollbacks
- error_feedback field addition

**No Telegram notification**:
```
[COUNCIL:KILO] ✅ Self-Diagnosis Upgrade Complete. error_handler injected...
```

This message was never sent.

---

## SUMMARY TABLE

| Requirement | Status | Details |
|-------------|--------|---------|
| error_feedback field | ❌ NO | Not in AgentState |
| LangGraph error_handler | ❌ NO | error_handler_node exists but not wired to tools |
| Conditional edge TTL | ⚠️ PARTIAL | At 5 loops, should be 3, should route to compensate |
| SAGA rollback | ⚠️ PARTIAL | Checkpoint system exists, but not explicit SAGA pattern |
| Agent prompt updates | ❌ NO | No error_feedback reading in prompts |
| Logging/notification | ❌ NO | No session log update or Telegram notification |

---

## THE CRITICAL GAP

**What should happen**:
1. Agent creates mutation
2. Mutation breaks during testing (Python error)
3. LangGraph error_handler fires automatically
4. Stack trace captured into `error_feedback`
5. State passed to agent with error info
6. Agent reads error_feedback in prompt
7. Agent proposes fix
8. If fix fails 3 times: SAGA rollback to stable state
9. System learns and moves on

**What actually happens**:
1. Agent creates mutation ✓
2. Mutation breaks during testing ✓
3. **Nothing captures the error** ❌
4. **error_feedback never populated** ❌
5. **Agent never sees error info** ❌
6. **Agent can't diagnose and fix** ❌
7. **Rollback happens without learning** ❌
8. **Next cycle proposes similar broken mutation** ❌

---

## WHAT NEEDS TO BE DONE

### Phase 1: Add Missing State Fields (30 min)
```python
# core/state.py
class AgentState(TypedDict):
    # ... existing fields ...
    error_feedback: Optional[str] = None
    error_trace: Optional[Dict[str, Any]] = None
    saga_transactions: List[Dict[str, Any]] = []
```

### Phase 2: Wire LangGraph Error Handler (60 min)
```python
# core/graph.py
def handle_tool_execution_error(state: AgentState, error: Exception) -> Dict:
    """Capture exception and inject into state"""
    return {
        "error_feedback": f"{type(error).__name__}: {str(error)}",
        "error_trace": {
            "exception": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc()
        },
        "loop_count": state["loop_count"] + 1
    }

# Attach to tool nodes
workflow.add_node("execute_mutation", execute_with_error_handler)
# Use LangGraph's error handler decorator/method
```

### Phase 3: Fix Conditional Edge (30 min)
```python
# core/graph.py
def deterministic_router(state: AgentState) -> str:
    if state["loop_count"] >= 3:  # Changed from 5 to 3
        return "compensate"  # Changed from terminal_fallback
    # ... rest of routing ...
```

### Phase 4: Add Compensate Node (60 min)
```python
# core/graph.py or core/rollback.py
def compensate_node(state: AgentState) -> Dict:
    """SAGA pattern rollback after loop exhaustion"""
    # Undo mutations in reverse order
    for transaction in reversed(state.get("saga_transactions", [])):
        restore_files(transaction["files_changed"], transaction["codebase_hash_before"])
    
    return {
        "messages": [{"role": "system", "content": "Rolled back to stable state"}],
        "loop_count": 0,
        "saga_transactions": []
    }
```

### Phase 5: Update Agent Prompts (60 min)
```python
# agents/alpha_evaluator.py and agents/beta_worker.py
if state.get("error_feedback"):
    prompt += f"""
    
    ⚠️ SELF-CORRECTION MODE ACTIVE
    Previous mutation failed:
    {state["error_feedback"]}
    
    Your task: Analyze the error and propose a revised mutation.
    """
```

### Phase 6: Log & Notify (30 min)
```python
# Add to session_log.md
# Update TODO.md
# Send Telegram notification
await send_telegram("[COUNCIL:KILO] ✅ Self-Diagnosis Complete...")
```

---

## TOTAL TIME ESTIMATE

- Phase 1: 30 min
- Phase 2: 60 min
- Phase 3: 30 min
- Phase 4: 60 min
- Phase 5: 60 min
- Phase 6: 30 min

**Total: ~4 hours**

---

## CONCLUSION

**The directive was NOT fully implemented.**

What exists:
- ✅ Basic error_handler_node
- ✅ loop_count circuit breaker
- ✅ Checkpoint system

What's missing:
- ❌ error_feedback field in state
- ❌ Actual LangGraph error handlers wired to tools
- ❌ Error trace capture and injection
- ❌ Agent prompts updated for self-diagnosis
- ❌ Explicit SAGA transaction tracking
- ❌ Compensate node routing
- ❌ Session log updates and Telegram notification

**The agents cannot yet self-diagnose and fix their own broken mutations.**

They can only rollback after failures, not learn from them.

