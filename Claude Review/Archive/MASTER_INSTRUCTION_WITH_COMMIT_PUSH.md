# MASTER INSTRUCTION TEMPLATE: Development Task Workflow

**For**: Kilo Code  
**Critical Requirement**: Read files + Commit + Push to GitHub  
**This prevents work from being lost in chat resets**

---

## BEFORE EACH TASK: READ THESE FILES

**EVERY TIME YOU START A NEW TASK, READ THESE FIRST:**

### 1. Read TODO.md
```bash
cat TODO.md | head -50
```
- See what's planned
- Check what's completed
- Understand remaining work

### 2. Read session_log.md
```bash
tail -100 session_log.md
```
- See what was done recently
- Understand context
- Don't repeat work

### 3. Check git log
```bash
git log --oneline | head -5
```
- See latest commits
- Verify work was pushed
- Know where you're starting from

---

## AFTER EACH TASK: COMMIT + PUSH (MANDATORY)

**DO NOT SKIP THIS STEP. This is how Martin verifies work.**

### Step 1: Verify work is done locally
```bash
# Test the feature works
pytest tests/test_X.py -v  # or run verification
# Should show: PASSED or ✓
```

### Step 2: Add all changes
```bash
git add .
```

### Step 3: Commit with clear message
```bash
git commit -m "Task X: [Description]

What was fixed/added: [Details]
Files changed: [List files]
Tests: [Show test results]"
```

### Step 4: Push to GitHub (CRITICAL)
```bash
git push
```

**IMPORTANT**: If you don't do `git push`, your work is not on GitHub. Martin can't see it.

### Step 5: Verify push succeeded
```bash
git log -1 --oneline
# Should show YOUR NEW COMMIT (not an old one)
```

**If it shows an old commit, YOUR PUSH FAILED. Try again:**
```bash
git push origin main  # Or whatever branch
```

### Step 6: Send Telegram notification
Send message to Martin:
```
Task X complete.
Commit: <SHA from git log -1 --oneline>
Files: <list>
Test result: <✓ or details>
```

---

## EXAMPLE: Task X Workflow

```bash
# 0. START OF TASK
# Read the pre-task files first!
cat TODO.md | head -30
tail -50 session_log.md
git log --oneline | head -3

# 1. DO THE WORK
# Follow task instructions in PHASE_X_TASKS_Y_Z.md
# Edit code, write tests, etc.

# 2. TEST LOCALLY
pytest tests/test_my_feature.py -v
# Output: PASSED ✓

# 3. COMMIT + PUSH (DO NOT SKIP)
git status  # See what changed
git add .
git commit -m "Task X: Fix checkpointer integration

Files changed: core/graph.py, tests/test_checkpointer.py
What was fixed: Replaced MemorySaver with JSONCheckpointer
Tests: test_persistence.py ✓
Verification: State persists across restart ✓"

git push  # PUSH TO GITHUB - MANDATORY

# 4. VERIFY PUSH
git log -1 --oneline
# Should show: abc1234 Task X: Fix checkpointer integration (NEW)

# 5. SEND TELEGRAM
# Send notification to Martin
# "Task X complete. Commit: abc1234. ✓"

# 6. DONE
# Wait for Martin's approval before next task
```

---

## CHECKLIST: Before Replying "Task Complete"

Before you tell Martin "Task X is complete", verify:

- [ ] Read TODO.md (checked context)
- [ ] Read session_log.md (knew what to do)
- [ ] Wrote/modified code (did the work)
- [ ] Tested locally (tests pass: PASSED ✓)
- [ ] Ran: `git add .` (staged changes)
- [ ] Ran: `git commit -m "..."` (created commit)
- [ ] Ran: `git push` (pushed to GitHub)
- [ ] Ran: `git log -1 --oneline` (verified commit on GitHub)
- [ ] Sent Telegram notification (Martin got message)
- [ ] Commit SHA in notification matches `git log -1`

**If you checked all 10 boxes, task is truly complete.**

---

## WHAT HAPPENS IF YOU DON'T PUSH

**Scenario: You finish Task X but don't push**

1. You tell Martin: "Task X complete"
2. Martin checks GitHub: No new commit
3. Martin: "I don't see commits"
4. You: "I did the work locally"
5. **Problem**: Martin can't verify. Work is lost if your session ends.

**Solution**: ALWAYS `git push` after commit.

---

## WHAT TO DO IF GIT PUSH FAILS

If you see error like:
```
fatal: unable to access 'https://github.com/...': Could not resolve host
```

**Try these:**

1. Check internet connection
```bash
ping github.com
```

2. Try with explicit branch:
```bash
git push origin main
```

3. If auth fails, check credentials:
```bash
git config --global user.name
git config --global user.email
```

4. If still failing, tell Martin: "Git push failed with: [error message]"

---

## SUMMARY: Critical Steps

**These three steps MUST happen for each task:**

1. ✅ **Do the work** (write code, pass tests)
2. ✅ **Commit** (`git commit -m "..."`)
3. ✅ **Push** (`git push`)

**If any are missing, work is lost.**

---

## FOR MARTIN: How to Verify

After Kilo says "Task X complete":

```bash
cd autonomousagent
git pull  # Get latest
git log -1 --oneline  # Should show new commit
git show ce2856f | head -50  # See what changed (use actual SHA)
```

**If new commit exists + code is right: APPROVED**  
**If no commit or wrong code: REJECTED, ask Kilo to redo**

---

**Remember: No push = no proof. No proof = no credit.**

