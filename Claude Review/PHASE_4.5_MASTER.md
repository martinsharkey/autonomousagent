# PHASE 4.5: MASTER INSTRUCTION - Mutation Wiring Fixes

**To**: Kilo Code  
**From**: Martin + Claude QA  
**Status**: Phase 4 mutations incomplete - need fixes before Phase 5  
**Urgency**: HIGH - blocks autonomous evolution  

---

## SITUATION REPORT

**What happened**:
- Phase 4 Tasks 13-16 completed (Grok verified)
- System now PROPOSES mutations based on performance
- But mutations don't actually CHANGE agent behavior

**Why**: 
- Agent parameters don't match mutation proposals
- Agents only load config at startup, not mid-session  
- Mutations never get approved/implemented in production

**Impact**:
- Autonomous evolution is NON-FUNCTIONAL
- Mutations proposed but ignored
- Agents can't learn from feedback

---

## WHAT YOU NEED TO DO

### STEP 1: Understand the Problem (5 minutes)

Read this FIRST:
```
FILE: MUTATION_AUDIT_REAL_OR_HALLUCINATED.md
WHY: Explains what's broken + why
TIME: 5 minutes
```

Key findings:
- ✅ Mutations ARE proposed (real)
- ❌ Parameters don't exist in code (hallucinated)
- ❌ Agents don't reload config (not wired)
- ❌ Mutations never reach "implemented" (stalled)

### STEP 2: Fix the 3 Blockers (1.25 hours)

Do these tasks IN ORDER:

```
FILE: PHASE_4.5_MUTATION_WIRING_FIXES.md
TASKS: 17, 18, 19
TIME: 75 minutes total
```

**Task 17** (20 min): Fix mutation parameters - use REAL agent variables  
**Task 18** (30 min): Make agents reload config mid-session  
**Task 19** (25 min): Wire approval → implementation automatically  

### STEP 3: Verify Everything Works (10 minutes)

Test the full cycle:
```bash
# Mutation proposal uses real parameters
# Mutation gets approved
# Agent loads new config mid-session
# Agent behavior changes
```

---

## REQUIRED PRE-TASK CHECKLIST

Before starting EACH task:

- [ ] Read TODO.md
- [ ] Read session_log.md
- [ ] Check git log (know where you're starting from)
- [ ] Read the task instructions carefully

---

## WORKFLOW (Same as Phase 4)

**For each task:**

1. Do the work (write code, test locally)
2. Commit: `git commit -m "Task X: ..."`
3. Push: `git push`
4. Verify: `git log -1 --oneline` (confirm SHA)
5. Reply: "Task X complete. Commit: <SHA>"

**Do NOT skip commit + push.** That's how Martin verifies.

---

## DOCUMENTS YOU NEED

### 1. MUTATION_AUDIT_REAL_OR_HALLUCINATED.md (READ FIRST)
- **What**: Diagnostic report on mutation system
- **Why**: Understand the problem before fixing it
- **Time**: 5 minutes

### 2. PHASE_4.5_MUTATION_WIRING_FIXES.md (DO THIS)
- **What**: 3 actionable tasks to fix the mutation system
- **Why**: Specific code changes to make mutations work
- **Time**: 75 minutes

### 3. MASTER_INSTRUCTION_WITH_COMMIT_PUSH.md (REFERENCE)
- **What**: Commit/push workflow + checklist
- **Why**: Make sure work gets saved to GitHub
- **Time**: Reference as needed

---

## CRITICAL DIFFERENCES FROM PHASE 4

**Phase 4**: Built the framework (mutations CAN work)  
**Phase 4.5**: Wire the framework (mutations ACTUALLY work)

**Phase 4 Tasks**:
- ✅ Added cycle_start scope fix
- ✅ Wired mutation → config → eval → promote
- ✅ Added Telegram NLP
- ✅ Set recursion limit

**Phase 4.5 Tasks** (fixing what was missed):
- ⚠️ Validate mutation parameters are REAL
- ⚠️ Make agents reload config MID-SESSION
- ⚠️ Auto-implement mutations after approval

---

## WHAT HAPPENS WHEN DONE

After Phase 4.5 (1.25 hours):

```
Agent performs task
    ↓
Trajectory recorded
    ↓
Feedback analyzes performance
    ↓
Mutation proposed based on real metrics
    ↓ (using REAL parameters like "temperature")
Council votes unanimously
    ↓
Mutation approved
    ↓ (auto-implements)
Config promoted to agent
    ↓
Agent reloads config MID-SESSION
    ↓ (not just at startup)
Agent uses new parameters
    ↓
Behavior ACTUALLY CHANGES
    ↓
Next iteration shows new performance
    ↓
✓ AUTONOMOUS EVOLUTION WORKS
```

---

## TIMELINE

| Phase | Tasks | Time | Status |
|-------|-------|------|--------|
| Phase 1 | 1-5 | 2 hrs | ✅ Complete |
| Phase 2 | 6-8 | 2 hrs | ✅ Complete |
| Phase 3 | 9-12 | 2 hrs | ✅ Complete |
| Phase 4 | 13-16 | 2 hrs | ✅ Complete (incomplete wiring) |
| **Phase 4.5** | **17-19** | **1.25 hrs** | 🔴 IN PROGRESS |
| Phase 5 | TBD | TBD | ⏳ Pending |

**Total to functional evolution**: ~9 hours  
**Current time invested**: ~8 hours  
**Remaining time**: 1.25 hours

---

## SUCCESS

**Phase 4.5 is complete when:**

- ✅ Mutation parameters validated (can't propose fake ones)
- ✅ Agents reload config mid-session (not just at startup)
- ✅ Mutations auto-implement after approval (not stalled)
- ✅ All 3 tasks committed + pushed to GitHub
- ✅ Full mutation cycle tested end-to-end

---

## GO

**Read these in order:**

1. **MUTATION_AUDIT_REAL_OR_HALLUCINATED.md** (understand problem)
2. **PHASE_4.5_MUTATION_WIRING_FIXES.md** (do the work)
3. **Start Task 17**

Reply when done with each task. Martin verifies via commit SHA.

---

**Questions?** Ask before starting, or flag issues during task completion.

**Ready to wire mutations?**

