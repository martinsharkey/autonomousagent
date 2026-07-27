# MASTER INSTRUCTION: Phase 3 + Telegram Notifications

**To**: Kilo Code  
**From**: Martin  
**Status**: Ready for final production push  
**Documents**: See both attached files

---

## TWO DOCUMENTS YOU NEED

### 1. PHASE_3_TASKS_9_12.md (THE WORK)
- Task 9: Fix checkpointer (30 min)
- Task 10: Fix HMAC secrets (15 min)
- Task 11: Expand .env.example (15 min)
- Task 12: Integration tests (1 hour)

### 2. TELEGRAM_NOTIFICATIONS_SETUP.md (THE NOTIFICATION)
- How to send Telegram message when task completes
- What to include in the message (proof)
- Example format
- Setup instructions if needed

---

## YOUR WORKFLOW FOR EACH TASK

### Step 1: Do the task
- Follow instructions in PHASE_3_TASKS_9_12.md
- Write code, test locally
- Verify it works

### Step 2: Commit and push
```bash
git add .
git commit -m "Task X: <description>"
git push
git log -1 --oneline  # Get the SHA
```

### Step 3: Send Telegram notification
Follow TELEGRAM_NOTIFICATIONS_SETUP.md:

**Option A (Script)**:
```bash
python send_notification.py
```

**Option B (Manual)**:
Send message manually to Martin via Telegram with format:
```
Task X complete.
Commit: <SHA>
Test: <result>
Files: <list>
```

### Step 4: Wait for approval
Martin reviews in Telegram. Once approved, start next task.

---

## EXAMPLE: Task 9 Complete → Notification

**Work**:
```bash
# Edit core/graph.py - replace MemorySaver with JSONCheckpointer
# Run test_persistence.py - ✓ PASSED
```

**Commit**:
```bash
git add core/graph.py
git commit -m "Task 9: Fix graph checkpointer integration"
git push
git log -1 --oneline
# Output: a1b2c3d4e5f6 Task 9: Fix graph checkpointer integration
```

**Telegram notification**:
```
Task 9 complete.
Commit: a1b2c3d4e5f6
Test: State persists across restart ✓
Files: core/graph.py
```

**Result**: Martin gets notification, reviews, approves.

---

## IMPORTANT RULES

1. **Do tasks in order**: 9 → 10 → 11 → 12
2. **Send notification after each commit**
3. **Include proof**: commit SHA, test results
4. **No [COUNCIL:*] prefixes** - you're the developer
5. **Wait for approval** before next task

---

## QUICK REFERENCE: Task Sequence

| Task | Time | What to test | Telegram format |
|------|------|--------------|-----------------|
| 9 | 30 min | State persists | `Task 9 complete. Commit: <SHA>. Test: Persists ✓. Files: core/graph.py` |
| 10 | 15 min | HMAC required | `Task 10 complete. Commit: <SHA>. Test: Required ✓. Files: zero_trust.py, .env.example, README` |
| 11 | 15 min | .env updated | `Task 11 complete. Commit: <SHA>. Updated: 6+ vars ✓. Files: .env.example` |
| 12 | 1 hour | 5 tests pass | `Task 12 complete. Commit: <SHA>. Tests: 5 passed ✓. Files: test_control_plane_e2e.py` |

---

## TOTAL TIME

4 tasks × average 30 min = **~2 hours**

After complete: **System is 95% done + production-ready**

---

## GO

Read both documents. Start Task 9. Send Telegram after commit.

Martin will be notified and reviewing in real-time.

