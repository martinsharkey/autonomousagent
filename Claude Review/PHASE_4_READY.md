# PHASE 4: Ready to Start - Autonomy Loop Integration

**To**: Kilo Code  
**Status**: Foundation complete (Phase 1-3), time to wire evolution  
**What's next**: 4 tasks to enable mutations → behavior changes  
**Total time**: ~2 hours

---

## WHAT PHASE 4 DOES

Currently the system:
- ✅ Can create goals
- ✅ Has consensus voting
- ✅ Has config versioning
- ❌ **Mutations don't actually change behavior**
- ❌ **Agent config isn't wired to evolution**
- ❌ **Telegram only understands /commands**

Phase 4 fixes those 3 things so evolution actually works.

---

## THE 4 TASKS

### Task 13: Fix cycle_start Scope Bug (15 min)
**File**: core/evolution.py line ~205  
**Problem**: `cycle_start` used but not defined in scope  
**Impact**: Goal tracking breaks  
**Priority**: 🔴 CRITICAL

### Task 14: Wire Mutation → Config → Eval → Promote (1 hour)
**File**: core/evolution.py  
**Problem**: _apply_mutation only logs, doesn't change anything  
**Fix**: Full pipeline: save config → evaluate → promote to agents  
**Impact**: CRITICAL - enables evolution to work

### Task 15: Add Telegram NLP (45 min)
**File**: core/telegram.py  
**Problem**: Only /commands, no plain language  
**Fix**: Add MessageHandler + LLM intent classification  
**Impact**: User-friendly, nice to have

### Task 16: Set Recursion Limit (5 min)
**File**: core/graph.py  
**Problem**: No recursion_limit (infinite loops possible)  
**Fix**: Add recursion_limit=25 to workflow.compile()  
**Impact**: Safety

---

## CRITICAL WORKFLOW (MUST DO)

**Before starting EACH task:**
1. Read TODO.md
2. Read session_log.md
3. Check git log

**After EACH task:**
1. Test locally (must pass)
2. **COMMIT**: `git commit -m "Task X: ..."`
3. **PUSH**: `git push` (MANDATORY - this is how Martin verifies)
4. **VERIFY**: `git log -1 --oneline` (confirm SHA shows up)
5. **REPLY**: "Task X complete. Commit: <SHA>"

**If you don't push, Martin can't verify. Work gets lost in chat resets.**

---

## DOCUMENTS YOU NEED

### 1. PHASE_4_TASKS_13_16.md
- Detailed instructions for each task
- Code examples
- Acceptance criteria
- Verification steps

### 2. MASTER_INSTRUCTION_WITH_COMMIT_PUSH.md
- Pre-task checklist (read TODO.md, session_log)
- Commit/push workflow
- Error handling
- Verification checklist

### 3. CLARITY_PHASE3_VS_GROK_P0.md (Reference)
- Explains why Phase 3 tasks are different from Grok's P0 items
- Both are true: Phase 3 done, Grok items still open

---

## EXAMPLE: Task 13 Complete Workflow

```bash
# 0. START
# Read the files
cat TODO.md | head -30
tail -50 session_log.md
git log --oneline | head -3

# 1. DO WORK
# Edit core/evolution.py
# Fix cycle_start scope bug
# Test locally
python -c "from core.evolution import Evolution; ..."
# ✓ cycle_start scope fixed

# 2. COMMIT + PUSH (MANDATORY)
git add .
git commit -m "Task 13: Fix cycle_start scope bug

Problem: cycle_start used but not defined in _select_and_execute_goal
Solution: Pass cycle_start as function parameter
Files: core/evolution.py (line 205)
Test: ✓ cycle_start scope fixed"

git push  # PUSH TO GITHUB
git log -1 --oneline
# Output: abc1234f Task 13: Fix cycle_start scope bug

# 3. REPLY
# "Task 13 complete. Commit: abc1234f. Status: cycle_start scope fixed"
```

---

## ACCEPTANCE: What "Complete" Means

✅ **Complete** = code is on GitHub:
- New commit in `git log --oneline`
- Commit message matches work done
- Code changes are in the files
- Tests pass locally

❌ **NOT complete** = work is only local:
- You did the work
- But didn't `git push`
- Commit doesn't show in `git log --oneline`
- Martin can't verify

---

## TIMELINE

| When | What |
|------|------|
| Now | Read Phase 4 task documents |
| Hour 1 | Task 13 (15min) + Task 14 (1hr) = 1.25 hours |
| Hour 2 | Task 15 (45min) + Task 16 (5min) = 50 minutes |
| After | System can evolve: mutations → config → behavior changes |

---

## SUCCESS CRITERIA

After Phase 4, the system can:
- ✅ Create goals via Telegram (plain language or /commands)
- ✅ Vote on mutations (unanimous consensus)
- ✅ Apply mutations (write to config store)
- ✅ Evaluate mutations (run tests)
- ✅ Promote mutations (agents load new config)
- ✅ Learn from feedback (actual behavior changes)

---

## KEY FILES TO KNOW

```
autonomousagent/
├── core/evolution.py          # Task 13 + 14 (scope fix + mutation wiring)
├── core/graph.py              # Task 16 (recursion_limit)
├── core/telegram.py           # Task 15 (NLP intent classification)
├── core/agent_config.py       # Used by Task 14 (config store)
├── core/evaluation.py         # Used by Task 14 (eval gate)
├── TODO.md                    # Read before each task
├── session_log.md             # Read before each task
└── tests/test_*.py            # Where to add tests
```

---

## SEND TO KILO

> "Phase 4 ready to start. Send two documents:
>
> **PHASE_4_TASKS_13_16.md** - The 4 tasks (13-16)  
> **MASTER_INSTRUCTION_WITH_COMMIT_PUSH.md** - Workflow (read TODO.md, commit+push)
>
> Critical: Read TODO.md + session_log BEFORE each task.  
> Critical: Commit + push after EACH task (this is how I verify).
>
> Tasks: 13 (15min) → 14 (1hr) → 15 (45min) → 16 (5min) = ~2 hours
>
> Start Task 13. Reply with commit SHA when done. Do not skip the commit+push step."

---

**Ready to send to Kilo?**

