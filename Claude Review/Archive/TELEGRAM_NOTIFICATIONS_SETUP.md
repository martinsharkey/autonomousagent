# Telegram Notifications: Task Completion

**For**: Kilo Code  
**Purpose**: Notify Martin when each task finishes  
**Format**: Proof-based, no impersonation

---

## HOW TO SEND TELEGRAM NOTIFICATION

After you finish each task (9, 10, 11, 12), send a Telegram message to Martin.

### Option A: Send Telegram Message via Python (Recommended)

Create a simple script to send the message:

```python
"""Send task completion notification to Telegram."""

import os
import requests

# Get credentials from env vars
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
    exit(1)

def send_notification(task_number, commit_sha, test_result, files_changed):
    """Send task completion notification."""
    
    message = f"""
🎯 Task {task_number} Complete

Commit: {commit_sha}
Test result: {test_result}
Files changed: {files_changed}

Ready for next task.
"""
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        print(f"✓ Notification sent for Task {task_number}")
    else:
        print(f"✗ Failed to send notification: {response.text}")

# Example: After completing Task 9
if __name__ == "__main__":
    send_notification(
        task_number=9,
        commit_sha="a1b2c3d4e5f6",
        test_result="State persists across restart: ✓",
        files_changed="core/graph.py"
    )
```

**Save as**: `send_notification.py`

**Run after each commit**:
```bash
python send_notification.py
```

---

### Option B: Send Message Manually via Telegram App

If script doesn't work, send message manually:

**Format**:
```
Task 9 complete.
Commit: a1b2c3d4e5f6
Test result: State persists: ✓
Files: core/graph.py
```

---

## WHAT THE MESSAGE SHOULD CONTAIN

### For Task 9 (Checkpointer):
```
Task 9 complete.
Commit: <SHA from git log -1 --oneline>
Test: State persists across restart ✓
Files: core/graph.py
```

### For Task 10 (HMAC Secrets):
```
Task 10 complete.
Commit: <SHA>
Test: HMAC_SECRET_KEY required, fails without it ✓
Files: governance/zero_trust.py, .env.example, README.md
```

### For Task 11 (.env.example):
```
Task 11 complete.
Commit: <SHA>
Updated: HMAC_SECRET_KEY, Telegram, Autonomy, Models vars ✓
Files: .env.example
```

### For Task 12 (Integration Tests):
```
Task 12 complete.
Commit: <SHA>
Tests: 5 passed (goal CRUD, persistence, priority, autonomy, health) ✓
Files: tests/test_control_plane_e2e.py
```

---

## IMPORTANT RULES

### ✅ DO:
- Send proof (commit SHA, test numbers)
- Say what you changed (file list)
- Use checkmarks (✓) for clarity
- Include task number (Task X)

### ❌ DON'T:
- Use [COUNCIL:*] prefixes (you're the developer)
- Claim to BE the system (you're Kilo, not Autobot)
- Send without proof
- Send generic messages without details

---

## STEP-BY-STEP: After Each Task

1. **Finish the task**
   - Code works
   - Tests pass
   - Verified locally

2. **Commit your work**
   ```bash
   git add .
   git commit -m "Task X: ..."
   git push
   ```

3. **Get commit SHA**
   ```bash
   git log -1 --oneline
   ```
   (First part is the SHA)

4. **Send Telegram notification**
   ```bash
   python send_notification.py  # Or send manually
   ```

5. **Wait for approval**
   - Martin verifies the work
   - Martin approves or asks for fixes

6. **Start next task**

---

## EXAMPLE: After Task 9

```bash
# 1. Finish task 9
python test_persistence.py  # ✓ PASSED

# 2. Commit
git add .
git commit -m "Task 9: Fix graph checkpointer integration"
git push

# 3. Get SHA
$ git log -1 --oneline
a1b2c3d4e5f6 Task 9: Fix graph checkpointer integration

# 4. Send notification
python send_notification.py

# Telegram receives:
# Task 9 complete.
# Commit: a1b2c3d4e5f6
# Test: State persists across restart ✓
# Files: core/graph.py
```

---

## TELEGRAM BOT SETUP (If Not Already Done)

If you don't have TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID set:

1. **Create Telegram bot** (if needed):
   - Talk to @BotFather on Telegram
   - Create new bot
   - Get bot token

2. **Find your chat ID**:
   - Send any message to your bot
   - Check: https://api.telegram.org/bot{BOT_TOKEN}/getUpdates
   - Find "chat" → "id"

3. **Set env vars**:
   ```bash
   export TELEGRAM_BOT_TOKEN="your_token_here"
   export TELEGRAM_CHAT_ID="your_chat_id_here"
   ```

4. **Test it**:
   ```bash
   python send_notification.py
   ```

---

## NOTIFICATION TIMING

Send notification **immediately after commit**, before moving to next task:

1. Finish task → Pass tests
2. Commit code → Push to GitHub
3. Send Telegram notification → Martin sees it
4. Martin reviews
5. Martin approves → Start next task

**Don't wait.** Send right after you commit.

---

## IF TELEGRAM DOESN'T WORK

If you can't get notifications working:

1. Try the script with error messages visible:
   ```bash
   python send_notification.py
   ```

2. If error: Tell me the error message

3. Fallback: Just reply here in chat:
   ```
   Task 9 complete.
   Commit: <SHA>
   ...
   ```

Martin will see it either way.

---

## SUMMARY

**After each task (9, 10, 11, 12):**

1. Test passes ✓
2. Commit + push ✓
3. Send Telegram:
   ```
   Task X complete.
   Commit: <SHA>
   Test: <result>
   Files: <list>
   ```
4. Wait for approval

Then move to next task.

---

Done. Add this section to your workflow for Tasks 9-12.

