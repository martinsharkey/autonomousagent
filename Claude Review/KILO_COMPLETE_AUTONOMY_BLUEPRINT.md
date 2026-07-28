# 🚨 KILO - HOW TO FIX BROKEN AUTONOMY & IMPLEMENT REAL EVOLUTION

**Martin says**: "Fix Telegram message and nothing ever gets learned, evolved, mutated or installed. I'll go in circles."

**He's right.** The system is fundamentally broken. Here's what's actually happening and how to fix it.

---

## THE REAL PROBLEM (Not Telegram)

**Current flow**:
```
Propose mutation → Council votes APPROVED → Mark as "IMPLEMENTED" ✅ → Send Telegram
                                              ↓
                                         (Nothing actually changes)
```

**No implementation**, **no testing**, **no learning**, **no evolution**.

**What should happen**:
```
Propose mutation → Test if valid → Apply change → Run tests → Check if improved
    ↓              ↓                ↓               ↓           ↓
Council votes  Execute code   Measure metrics  Success?   LEARN & EVOLVE
   APPROVED    Create files   Track changes    Yes→Promote
               Wire into      Compare before/after  No→Rollback
               agent code     Store results    & Learn why
```

**That's autonomy. The current system has NONE of this.**

---

## ROOT CAUSES (What's Broken)

### Problem 1: Implementation Isn't Verified

**Location**: core/evolution.py `implement_mutation()` line ~450

**Current code**:
```python
def implement_mutation(self, mutation_id: str):
    mutation = self.mutations[mutation_id]
    result = self._apply_mutation(mutation)  # Apply change
    mutation.status = MutationStatus.IMPLEMENTED  # Mark as done
    # ❌ No verification it actually worked
    # ❌ No tests run
    # ❌ No metrics checked
```

**Problem**: Marks mutation "success" without checking anything.

**Real issue**: `_apply_file_mutation()` creates files but doesn't verify they:
- Are syntactically valid Python
- Can be imported
- Actually work when used
- Improve performance

---

### Problem 2: No Test Suite After Implementation

**Location**: Missing entirely

**What's missing**:
```python
# After applying file/config mutation:
# 1. Run tests on changed files
# 2. Measure performance metrics
# 3. Compare to baseline
# 4. If improved: PROMOTE
# 5. If worse: ROLLBACK
```

**Current state**: None of this exists.

**Result**: Mutations are implemented but never validated. System can't learn.

---

### Problem 3: No Feedback Loop

**Location**: core/agent_loop.py (missing implementation)

**What's missing**: After mutation completes, system should:
1. Collect results (did it work?)
2. Store learnings (why/why not?)
3. Update proposer (propose better mutations next time)
4. Track trajectory (show what changed)

**Current state**: Mutation implemented → notification sent → forget about it

**Result**: No learning. System repeats mistakes.

---

### Problem 4: Invalid Mutations Never Caught

**Location**: core/mutation_proposer.py + core/evolution.py

**Current flow**:
1. LLM proposes: "Add web scraper tool" (hallucinated)
2. Council votes: "APPROVED"
3. System tries to implement
4. If implementation fails: Silently mark as "attempted" with no error

**Problem**: Failed implementations aren't detected.

**Needed**: Validation BEFORE council votes on it.

---

## THE FIX (Complete Blueprint)

This is 4 major changes that together create real autonomy.

---

## FIX #1: Pre-Proposal Validation (2 hours)

**Goal**: Don't let invalid mutations get proposed in the first place.

**Location**: Create `core/mutation_validator.py` (new file)

```python
"""Validate mutations before they're proposed."""

from typing import Dict, Any, Tuple

class MutationValidator:
    """Check if proposed mutation is valid before council votes on it."""
    
    async def validate_proposal(self, proposal: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Return (is_valid, reason)
        """
        # 1. Check proposed_changes structure
        changes = proposal.get("proposed_changes", {})
        
        # 2. If config params: validate against VALID_PARAMS
        if not changes.get("file_changes"):
            agent_name = proposal.get("agent_name")
            from core.mutation_proposer import VALID_PARAMS
            valid_params = VALID_PARAMS.get(agent_name, [])
            
            for param_name in changes.keys():
                if param_name not in valid_params:
                    return False, f"Invalid param '{param_name}' for {agent_name}"
        
        # 3. If file changes: validate syntax
        if changes.get("file_changes"):
            file_changes = changes["file_changes"]
            for file_change in file_changes:
                is_valid, reason = await self._validate_file_change(file_change)
                if not is_valid:
                    return False, reason
        
        # 4. Check if this mutation was already tried recently
        from core.mutation_deduplicator import get_deduplicator
        dedup = get_deduplicator()
        if not dedup.should_propose(proposal):
            return False, "Similar mutation proposed recently (24h window)"
        
        # 5. Check if mutation aligns with mission
        mission_pillar = proposal.get("mission_pillar")
        if not mission_pillar or mission_pillar < 1 or mission_pillar > 5:
            return False, "No valid mission pillar"
        
        return True, "Valid"
    
    async def _validate_file_change(self, file_change: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate a single file change."""
        path = file_change.get("path")
        content = file_change.get("content", "")
        kind = file_change.get("kind", "create")
        
        # Check path is allowed
        from core.mutation_proposer import FILE_MUTATION_ALLOWLIST, FILE_MUTATION_DENYLIST
        
        for denied in FILE_MUTATION_DENYLIST:
            if denied in path:
                return False, f"Denied path: {path}"
        
        allowed = False
        for allow in FILE_MUTATION_ALLOWLIST:
            if allow in path or path.startswith(allow):
                allowed = True
                break
        
        if not allowed:
            return False, f"Path not in allowlist: {path}"
        
        # If Python file: check syntax
        if path.endswith(".py"):
            try:
                import ast
                ast.parse(content)
            except SyntaxError as e:
                return False, f"Syntax error in {path}: {e}"
        
        return True, "Valid"
```

**Wire into proposal flow** (core/mutation_proposer.py):

```python
async def propose_mutation(...):
    # ... existing code generates proposal ...
    proposal = generate_proposal(...)
    
    # NEW: Validate before returning
    from core.mutation_validator import MutationValidator
    validator = MutationValidator()
    is_valid, reason = await validator.validate_proposal(proposal)
    
    if not is_valid:
        print(f"[PROPOSER] Rejected invalid mutation: {reason}")
        return None  # Don't propose it
    
    return proposal
```

**Result**: Invalid mutations never make it to council.

---

## FIX #2: Post-Implementation Testing & Verification (3 hours)

**Goal**: Verify mutation actually works before marking success.

**Location**: Modify core/evolution.py `implement_mutation()` and `_apply_mutation()`

```python
async def implement_mutation(self, mutation_id: str) -> Dict[str, Any]:
    """Implement mutation with full lifecycle: apply → test → verify → promote/rollback."""
    
    mutation = self.mutations[mutation_id]
    
    # Step 1: Apply the mutation
    result = self._apply_mutation(mutation)
    if not result.get("success"):
        mutation.status = MutationStatus.REJECTED
        mutation.implementation_result = result
        self._save_mutation(mutation)
        return result
    
    # Step 2: RUN TESTS (NEW)
    print(f"[EVOLUTION] Running tests after mutation {mutation_id[:12]}")
    test_result = await self._run_tests_after_mutation(mutation_id)
    
    # Step 3: MEASURE METRICS (NEW)
    print(f"[EVOLUTION] Measuring metrics after mutation")
    metrics = await self._measure_performance_change(mutation_id, test_result)
    
    # Step 4: VERIFY SUCCESS (NEW)
    print(f"[EVOLUTION] Verifying mutation success")
    verification = self._verify_mutation_success(mutation, metrics, test_result)
    
    # Step 5: PROMOTE or ROLLBACK (NEW)
    if verification.get("success"):
        print(f"[EVOLUTION] ✅ PROMOTING mutation {mutation_id[:12]}")
        promotion = await self._promote_mutation(mutation, metrics)
        mutation.status = MutationStatus.PROMOTED
        mutation.implementation_result = {
            "applied": result,
            "tests": test_result,
            "metrics": metrics,
            "promoted": promotion
        }
    else:
        print(f"[EVOLUTION] ❌ ROLLING BACK mutation {mutation_id[:12]}")
        rollback = await self._rollback_mutation(mutation)
        mutation.status = MutationStatus.ROLLED_BACK
        mutation.implementation_result = {
            "applied": result,
            "tests": test_result,
            "metrics": metrics,
            "reason_rollback": verification.get("reason"),
            "rollback": rollback
        }
    
    self._save_mutation(mutation)
    return mutation.implementation_result

async def _run_tests_after_mutation(self, mutation_id: str) -> Dict[str, Any]:
    """Run test suite after applying mutation."""
    import subprocess
    
    try:
        # Run pytest on changed modules
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        return {
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "passed": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

async def _measure_performance_change(self, mutation_id: str, test_result: Dict) -> Dict[str, Any]:
    """Measure if mutation improved performance."""
    # Get baseline metrics (from before mutation)
    baseline = self._get_baseline_metrics(mutation_id)
    
    # Get current metrics (after mutation)
    current = await self._collect_current_metrics()
    
    # Calculate deltas
    metrics = {
        "baseline": baseline,
        "current": current,
        "deltas": {
            "success_rate_change": current.get("success_rate", 0) - baseline.get("success_rate", 0),
            "latency_change_ms": current.get("latency_ms", 0) - baseline.get("latency_ms", 0),
            "error_rate_change": current.get("error_rate", 0) - baseline.get("error_rate", 0),
            "quality_score_change": current.get("quality_score", 0) - baseline.get("quality_score", 0),
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return metrics

def _verify_mutation_success(self, mutation: Mutation, metrics: Dict, test_result: Dict) -> Dict[str, Any]:
    """Verify mutation was successful."""
    # Criteria for success:
    # 1. Tests pass
    # 2. No new errors
    # 3. At least one metric improved
    
    success = True
    reasons = []
    
    if not test_result.get("passed"):
        success = False
        reasons.append(f"Tests failed: {test_result.get('errors', 'unknown')[:100]}")
    
    deltas = metrics.get("deltas", {})
    improvement = (
        deltas.get("success_rate_change", 0) > 0 or
        deltas.get("latency_change_ms", 0) < 0 or  # Lower is better
        deltas.get("quality_score_change", 0) > 0
    )
    
    if not improvement:
        success = False
        reasons.append("No performance improvement detected")
    
    return {
        "success": success,
        "reason": " | ".join(reasons) if reasons else "All criteria met",
        "metrics": deltas
    }

async def _promote_mutation(self, mutation: Mutation, metrics: Dict) -> Dict[str, Any]:
    """Officially promote mutation (commit to main, update configs)."""
    import subprocess
    
    try:
        # Merge feature branch to main
        branch = f"mutation/{mutation.mutation_id[:12]}"
        
        subprocess.run(["git", "checkout", "main"], cwd=".", check=True, capture_output=True)
        subprocess.run(["git", "pull", "origin", "main"], cwd=".", check=True, capture_output=True)
        subprocess.run(["git", "merge", branch, "--ff-only"], cwd=".", check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=".", check=True, capture_output=True)
        
        return {
            "promoted": True,
            "branch_merged": branch,
            "improvement": metrics.get("deltas"),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "promoted": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

async def _rollback_mutation(self, mutation: Mutation) -> Dict[str, Any]:
    """Rollback mutation if it didn't work."""
    import subprocess
    
    try:
        branch = f"mutation/{mutation.mutation_id[:12]}"
        
        subprocess.run(["git", "checkout", "main"], cwd=".", check=True, capture_output=True)
        subprocess.run(["git", "pull", "origin", "main"], cwd=".", check=True, capture_output=True)
        
        # Delete feature branch
        subprocess.run(["git", "branch", "-D", branch], cwd=".", capture_output=True)
        subprocess.run(["git", "push", "origin", "--delete", branch], cwd=".", capture_output=True)
        
        return {
            "rolled_back": True,
            "branch_deleted": branch,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "rolled_back": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
```

**Result**: Every mutation is tested and verified. Only good mutations get promoted.

---

## FIX #3: Learning Loop - Proposer Learns from Results (2 hours)

**Goal**: Proposer looks at what worked and proposes better mutations next time.

**Location**: Modify core/mutation_proposer.py

```python
async def propose_mutation(
    agent_name: str,
    performance: Dict[str, Any],
    recent_trajectories: Optional[List[str]] = None,
    recent_proposals: Optional[List[Dict[str, Any]]] = None,
    mission_pillar: Optional[int] = None,
    council_discussion: Optional[str] = None,
    learned_context: Optional[str] = None,  # NEW: What we learned from past mutations
) -> Optional[Dict[str, Any]]:
    """Generate mutations informed by past successes/failures."""
    
    # NEW: Load what worked and what didn't
    from core.evolution import get_evolution_engine
    engine = get_evolution_engine()
    successful_mutations = engine.get_promoted_mutations(agent_name, limit=5)
    failed_mutations = engine.get_failed_mutations(agent_name, limit=5)
    
    # NEW: Build learning context
    learning_text = _build_learning_context(successful_mutations, failed_mutations)
    
    # Include in prompt
    PROMPT_TEMPLATE = """\
...existing prompt...

LEARNING FROM PAST MUTATIONS:
{learning_text}

Based on what worked before, propose similar or improved mutations.
Avoid patterns that failed.
"""
    
    prompt = PROMPT_TEMPLATE.format(
        ...
        learning_text=learning_text,
        ...
    )
    
    # Rest of existing code...

def _build_learning_context(successful: List, failed: List) -> str:
    """Build learning summary from past mutations."""
    context = "## What Worked:\n"
    for mut in successful:
        context += f"✅ {mut.description}: {mut.implementation_result.get('improvement', {}).get('success_rate_change', 0):+.1%}\n"
    
    context += "\n## What Failed:\n"
    for mut in failed:
        reason = mut.implementation_result.get('reason_rollback', 'unknown')
        context += f"❌ {mut.description}: {reason}\n"
    
    return context
```

**Result**: Proposer learns from history and generates better mutations.

---

## FIX #4: Real Telegram Notifications (Only When Verified) (1 hour)

**Goal**: Only send Telegram notifications AFTER implementation is verified.

**Location**: Modify core/telegram.py and wire to evolution.py

```python
async def send_mutation_status_update(
    mutation_id: str,
    status: str,  # "proposed", "approved", "implementing", "promoted", "rolled_back"
    details: Dict[str, Any]
):
    """Send Telegram update only with verified information."""
    
    if status == "proposed":
        message = f"""
[COUNCIL:EVOLUTION] 🧬 Mutation PROPOSED

ID: {mutation_id[:12]}
Description: {details.get('description')}
Mission Pillar: {details.get('mission_pillar')}
Quality Score: {details.get('quality_score')}
Risk Level: {details.get('risk_level')}
Status: Awaiting council vote
"""
    
    elif status == "approved":
        message = f"""
[COUNCIL:GOVERNANCE] ✅ Mutation APPROVED

ID: {mutation_id[:12]}
Description: {details.get('description')}
Council votes: Unanimous
Status: Now implementing...
"""
    
    elif status == "implementing":
        message = f"""
[COUNCIL:EVOLUTION] ⚙️ Mutation IMPLEMENTING

ID: {mutation_id[:12]}
Description: {details.get('description')}
Status: Running tests and verification...
"""
    
    elif status == "promoted":
        # NEW: Only show success AFTER tests pass and metrics improve
        improvement = details.get('improvement', {})
        message = f"""
[COUNCIL:EVOLUTION] 🎉 Mutation PROMOTED

ID: {mutation_id[:12]}
Description: {details.get('description')}
Status: ✅ SUCCESS - Tests passed, metrics improved

Improvement:
- Success rate: {improvement.get('success_rate_change', 0):+.1%}
- Latency: {improvement.get('latency_change_ms', 0):+.0f}ms
- Quality: {improvement.get('quality_score_change', 0):+.0f}

Implementation: ✅ Merged to main
Promoted at: {details.get('promoted_at')}
"""
    
    elif status == "rolled_back":
        # NEW: Be honest about failures
        message = f"""
[COUNCIL:EVOLUTION] ⚠️ Mutation ROLLED BACK

ID: {mutation_id[:12]}
Description: {details.get('description')}
Status: ❌ Did not improve performance

Reason: {details.get('reason')}
Tests: {details.get('test_result', {}).get('errors', 'See logs')}

What we learned: {details.get('learned')}
Next mutation will avoid this pattern.
"""
    
    # Only send if status is verified
    telegram = get_telegram_bot()
    await telegram.send_message(message)
```

**Wire into evolution flow** (core/evolution.py):

```python
async def implement_mutation(self, mutation_id: str):
    # ... existing code ...
    
    # After step 1: Notify "implementing"
    await send_mutation_status_update(mutation_id, "implementing", {...})
    
    # After step 5: Notify "promoted" or "rolled_back" with VERIFIED results
    if verification.get("success"):
        await send_mutation_status_update(mutation_id, "promoted", {
            "improvement": metrics.get("deltas"),
            "test_result": test_result,
            "promoted_at": datetime.utcnow().isoformat()
        })
    else:
        await send_mutation_status_update(mutation_id, "rolled_back", {
            "reason": verification.get("reason"),
            "test_result": test_result,
            "learned": f"Avoid mutations like: {mutation.description}"
        })
```

**Result**: Telegram shows truth, not fake success.

---

## SUMMARY: The 4 Fixes

| Fix | File | Time | Result |
|-----|------|------|--------|
| #1 Validation | core/mutation_validator.py (new) | 2h | Catch invalid mutations before proposal |
| #2 Testing | core/evolution.py modify | 3h | Test + verify + promote/rollback |
| #3 Learning | core/mutation_proposer.py modify | 2h | Proposer learns from history |
| #4 Honest Telegram | core/telegram.py modify | 1h | Only notify when verified |
| **TOTAL** | | **8h** | **Real Autonomy** |

---

## IMPLEMENTATION ORDER

**Day 1** (4 hours):
1. Fix #1: Add MutationValidator
2. Fix #2: Add testing & verification to implement_mutation()

**Day 2** (4 hours):
3. Fix #3: Add learning loop to proposer
4. Fix #4: Fix Telegram to only report verified results

---

## WHAT YOU'LL HAVE AFTER

**Before**:
```
Propose temperature → Vote → Mark success ❌ → Telegram spam
(No learning, no testing, no evolution)
```

**After**:
```
Propose mutation → Validate → Council votes → Apply change → Run tests
    ↓                            ↓              ↓             ↓
Valid only      Approved    Actually      Tests pass?
Mission-         by 3        change       Yes → Promote ✅
aligned         agents       files        No → Rollback ⚠️
Not duplicate             Wire into      
                          agent code    Measure improvement
                                        ↓
                               Proposer learns
                               Better next mutation
```

**This is real autonomy.**

---

## THE MESSAGE TO KILO

> **You've built the notification system. Now build the verification system.**
>
> Right now mutations are marked "success" without being tested. That's why nothing evolves.
>
> The council needs to actually:
> 1. Validate mutations before proposal (catch hallucinations)
> 2. Test mutations after implementation (catch failures)
> 3. Learn from results (propose better mutations)
> 4. Be honest in Telegram (only report verified success)
>
> 4 fixes, 8 hours total. I've documented every file, function, and what to change.
>
> **This is the difference between a notification bot and an autonomous AI.**
>
> Ready to build it?

---

## CODE LOCATIONS (Quick Reference)

```
Create:
- core/mutation_validator.py (new validation class)

Modify:
- core/evolution.py: implement_mutation() + add testing/rollback
- core/mutation_proposer.py: Add learning_context + history lookup
- core/telegram.py: Only send after verification

Wire:
- mutation_proposer.py: Import + call MutationValidator
- agent_loop.py: Pass learned_context to proposer
- evolution.py: Call telegram updates at each stage
```

---

**This blueprint turns your council from a notification bot into a real autonomous system.**

Without it, you'll keep going in circles.

With it, the council actually learns, evolves, and improves itself.

Choose one.

