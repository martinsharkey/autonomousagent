"""GitHub Issues ↔ Council GoalStore bidirectional sync.

Enables the council to:
- Read GitHub Issues as actionable goals
- Create issues when it identifies new work
- Update issues when goals are completed/failed
- Sync roadmap status back to GitHub

Uses `gh` CLI (requires GitHub CLI installed and authenticated).
"""

import json
import subprocess
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYNC_STATE_FILE = PROJECT_ROOT / "evolution" / "github_sync_state.json"

# Label mapping between council priority levels and GitHub labels
PRIORITY_LABELS = {
    100: "priority: critical",
    75: "priority: high",
    50: "priority: medium",
    25: "priority: low",
    10: "priority: background",
}

# Status mapping: GoalStore status → GitHub Issue state
STATUS_TO_GITHUB = {
    "completed": "closed",
    "failed": "closed",  # Close with label
    "cancelled": "closed",
    "pending": "open",
    "in_progress": "open",
    "blocked": "open",
}

# Label for council-created issues
COUNCIL_LABEL = "council-managed"
ROADMAP_LABEL = "roadmap"


def _run_gh(args: List[str], check: bool = True) -> Tuple[bool, str, str]:
    """Run a gh CLI command."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=30,
        )
        if check and result.returncode != 0:
            return False, result.stdout, result.stderr
        return True, result.stdout, result.stderr
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, "", str(e)


def _load_sync_state() -> Dict[str, Any]:
    """Load sync state (maps goal_id ↔ issue_number)."""
    try:
        if SYNC_STATE_FILE.exists():
            with open(SYNC_STATE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {"goal_to_issue": {}, "issue_to_goal": {}, "last_sync": None}


def _save_sync_state(state: Dict[str, Any]) -> None:
    """Persist sync state."""
    try:
        SYNC_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state["last_sync"] = datetime.now().isoformat()
        with open(SYNC_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


# ─── READ: Pull GitHub Issues into council awareness ───────────────────────

def list_open_issues(labels: Optional[List[str]] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """List open GitHub Issues as structured data.
    
    Returns list of dicts with: number, title, body, labels, assignee, created_at
    """
    args = ["issue", "list", "--state", "open", "--limit", str(limit), "--json",
            "number,title,body,labels,assignees,createdAt,updatedAt"]
    if labels:
        args.extend(["--label", ",".join(labels)])
    
    ok, stdout, stderr = _run_gh(args)
    if not ok:
        print(f"[GITHUB_SYNC] Failed to list issues: {stderr}")
        return []
    
    try:
        issues = json.loads(stdout)
        return issues
    except (json.JSONDecodeError, TypeError):
        return []


def get_issue(issue_number: int) -> Optional[Dict[str, Any]]:
    """Get a specific issue by number."""
    args = ["issue", "view", str(issue_number), "--json",
            "number,title,body,labels,assignees,state,createdAt,updatedAt,comments"]
    
    ok, stdout, stderr = _run_gh(args)
    if not ok:
        return None
    
    try:
        return json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        return None


# ─── WRITE: Create/Update GitHub Issues from council ───────────────────────

def create_issue(
    title: str,
    body: str,
    labels: Optional[List[str]] = None,
    assignee: Optional[str] = None,
    priority: int = 50,
) -> Optional[int]:
    """Create a new GitHub Issue from council activity.
    
    Returns issue number on success, None on failure.
    """
    all_labels = [COUNCIL_LABEL]
    if labels:
        all_labels.extend(labels)
    
    # Add priority label
    priority_label = PRIORITY_LABELS.get(priority)
    if priority_label:
        all_labels.append(priority_label)
    
    args = ["issue", "create", "--title", title, "--body", body]
    for label in all_labels:
        args.extend(["--label", label])
    if assignee:
        args.extend(["--assignee", assignee])
    
    ok, stdout, stderr = _run_gh(args)
    if not ok:
        print(f"[GITHUB_SYNC] Failed to create issue: {stderr}")
        return None
    
    # Parse issue URL to get number
    # gh outputs: https://github.com/user/repo/issues/38
    try:
        url = stdout.strip()
        issue_number = int(url.rstrip("/").split("/")[-1])
        print(f"[GITHUB_SYNC] Created issue #{issue_number}: {title}")
        return issue_number
    except (ValueError, IndexError):
        print(f"[GITHUB_SYNC] Created issue but couldn't parse number from: {stdout}")
        return None


def close_issue(issue_number: int, comment: Optional[str] = None) -> bool:
    """Close a GitHub Issue (when goal is completed/failed)."""
    if comment:
        _run_gh(["issue", "comment", str(issue_number), "--body", comment], check=False)
    
    ok, _, stderr = _run_gh(["issue", "close", str(issue_number)])
    if ok:
        print(f"[GITHUB_SYNC] Closed issue #{issue_number}")
    else:
        print(f"[GITHUB_SYNC] Failed to close issue #{issue_number}: {stderr}")
    return ok


def add_issue_comment(issue_number: int, comment: str) -> bool:
    """Add a comment to an existing issue (progress updates)."""
    ok, _, stderr = _run_gh(["issue", "comment", str(issue_number), "--body", comment])
    if not ok:
        print(f"[GITHUB_SYNC] Failed to comment on #{issue_number}: {stderr}")
    return ok


def update_issue_labels(issue_number: int, add_labels: List[str] = None, remove_labels: List[str] = None) -> bool:
    """Add or remove labels from an issue."""
    success = True
    if add_labels:
        for label in add_labels:
            ok, _, _ = _run_gh(["issue", "edit", str(issue_number), "--add-label", label], check=False)
            if not ok:
                success = False
    if remove_labels:
        for label in remove_labels:
            ok, _, _ = _run_gh(["issue", "edit", str(issue_number), "--remove-label", label], check=False)
            if not ok:
                success = False
    return success


# ─── SYNC: Bidirectional sync between GoalStore and GitHub Issues ──────────

def sync_issues_to_goals() -> Dict[str, Any]:
    """Pull open GitHub Issues and create goals for any not already tracked.
    
    Returns summary of sync actions taken.
    """
    from core.goals import get_goal_store, GoalPriority
    
    state = _load_sync_state()
    goal_store = get_goal_store()
    issues = list_open_issues()
    
    created = 0
    skipped = 0
    
    for issue in issues:
        issue_num = str(issue["number"])
        
        # Skip if already synced
        if issue_num in state["issue_to_goal"]:
            skipped += 1
            continue
        
        # Determine priority from labels
        priority = 50  # default medium
        labels = [l.get("name", "") for l in issue.get("labels", [])]
        for prio_val, prio_label in PRIORITY_LABELS.items():
            if prio_label in labels:
                priority = prio_val
                break
        
        # Create goal from issue
        title = issue.get("title", "Untitled")
        body = issue.get("body", "") or ""
        description = f"[GitHub #{issue_num}] {title}"
        if body:
            description += f"\n\n{body[:500]}"
        
        # Determine source
        source = "github_issue"
        if COUNCIL_LABEL in labels:
            source = "council"  # It was created by the council itself
        
        try:
            goal_id = goal_store.create_goal(
                description=description,
                source=source,
                priority=priority,
                metadata={"github_issue": int(issue_num), "labels": labels}
            )
            
            # Track the mapping
            state["goal_to_issue"][goal_id] = issue_num
            state["issue_to_goal"][issue_num] = goal_id
            created += 1
            print(f"[GITHUB_SYNC] Issue #{issue_num} → Goal {goal_id[:8]}")
        except Exception as e:
            print(f"[GITHUB_SYNC] Failed to create goal for #{issue_num}: {e}")
    
    _save_sync_state(state)
    
    return {
        "issues_found": len(issues),
        "goals_created": created,
        "skipped_existing": skipped,
    }


def sync_goals_to_issues() -> Dict[str, Any]:
    """Push goal status updates back to GitHub Issues.
    
    - Completed goals → close the linked issue with a comment
    - Failed goals → add failure comment
    - In-progress goals → add progress comment
    """
    from core.goals import get_goal_store
    
    state = _load_sync_state()
    goal_store = get_goal_store()
    
    closed = 0
    commented = 0
    
    for goal_id, issue_num in list(state["goal_to_issue"].items()):
        try:
            goal = goal_store.get_goal(goal_id)
            if not goal:
                continue
            
            status = goal.get("status", "pending")
            
            if status == "completed":
                comment = (
                    f"✅ **Goal completed by council**\n\n"
                    f"Agent: {goal.get('assigned_to', 'unassigned')}\n"
                    f"Completed: {goal.get('updated_at', 'unknown')}\n"
                )
                if close_issue(int(issue_num), comment):
                    closed += 1
                    # Remove from tracking (don't re-process)
                    del state["goal_to_issue"][goal_id]
                    del state["issue_to_goal"][issue_num]
                    
            elif status == "failed":
                comment = (
                    f"❌ **Goal failed**\n\n"
                    f"Agent: {goal.get('assigned_to', 'unassigned')}\n"
                    f"Status: {status}\n"
                    f"The council will retry or escalate.\n"
                )
                add_issue_comment(int(issue_num), comment)
                commented += 1
                
        except Exception as e:
            print(f"[GITHUB_SYNC] Error syncing goal {goal_id}: {e}")
    
    _save_sync_state(state)
    
    return {
        "issues_closed": closed,
        "issues_commented": commented,
    }


def full_sync() -> Dict[str, Any]:
    """Run full bidirectional sync: Issues→Goals then Goals→Issues."""
    result = {
        "inbound": sync_issues_to_goals(),
        "outbound": sync_goals_to_issues(),
        "timestamp": datetime.now().isoformat(),
    }
    print(f"[GITHUB_SYNC] Full sync complete: {result['inbound']['goals_created']} new goals, "
          f"{result['outbound']['issues_closed']} issues closed")
    return result


# ─── COUNCIL TOOLS: Functions the council can call during goal execution ───

def council_create_issue(
    title: str,
    body: str,
    priority: int = 50,
    labels: Optional[List[str]] = None,
) -> Optional[int]:
    """Council-facing tool to create a new GitHub Issue and link it to a goal.
    
    Used when the council identifies new work (bugs, features, improvements).
    """
    issue_num = create_issue(title, body, labels=labels, priority=priority)
    if issue_num is None:
        return None
    
    # Also create a corresponding goal
    from core.goals import get_goal_store
    
    state = _load_sync_state()
    goal_store = get_goal_store()
    
    try:
        goal_id = goal_store.create_goal(
            description=f"[GitHub #{issue_num}] {title}\n\n{body[:500]}",
            source="council",
            priority=priority,
            metadata={"github_issue": issue_num, "labels": labels or []}
        )
        state["goal_to_issue"][goal_id] = str(issue_num)
        state["issue_to_goal"][str(issue_num)] = goal_id
        _save_sync_state(state)
    except Exception as e:
        print(f"[GITHUB_SYNC] Goal creation failed for issue #{issue_num}: {e}")
    
    return issue_num


def council_report_progress(goal_id: str, progress_text: str) -> bool:
    """Council reports progress on a goal — synced as GitHub Issue comment."""
    state = _load_sync_state()
    issue_num = state["goal_to_issue"].get(goal_id)
    if not issue_num:
        return False
    
    comment = f"🔄 **Council progress update**\n\n{progress_text}"
    return add_issue_comment(int(issue_num), comment)


# ─── ROADMAP GENERATION ────────────────────────────────────────────────────

def generate_github_roadmap() -> str:
    """Generate a roadmap view from GitHub Issues for council context.
    
    Returns a markdown summary the council can use for planning.
    """
    issues = list_open_issues(limit=30)
    if not issues:
        return "No open GitHub Issues found."
    
    # Group by priority
    critical = []
    high = []
    medium = []
    low = []
    other = []
    
    for issue in issues:
        labels = [l.get("name", "") for l in issue.get("labels", [])]
        title = f"#{issue['number']}: {issue['title']}"
        
        if "priority: critical" in labels:
            critical.append(title)
        elif "priority: high" in labels:
            high.append(title)
        elif "priority: medium" in labels:
            medium.append(title)
        elif "priority: low" in labels:
            low.append(title)
        else:
            other.append(title)
    
    lines = ["## GitHub Issues Roadmap\n"]
    
    if critical:
        lines.append("### 🔴 Critical")
        for item in critical:
            lines.append(f"- {item}")
        lines.append("")
    
    if high:
        lines.append("### 🟠 High")
        for item in high:
            lines.append(f"- {item}")
        lines.append("")
    
    if medium:
        lines.append("### 🟡 Medium")
        for item in medium:
            lines.append(f"- {item}")
        lines.append("")
    
    if low:
        lines.append("### 🟢 Low")
        for item in low:
            lines.append(f"- {item}")
        lines.append("")
    
    if other:
        lines.append("### ⚪ Unprioritized")
        for item in other:
            lines.append(f"- {item}")
        lines.append("")
    
    return "\n".join(lines)


# ─── SINGLETON ─────────────────────────────────────────────────────────────

_sync_instance = None

def get_github_sync():
    """Get the sync module (for use in agent tools)."""
    return {
        "list_issues": list_open_issues,
        "get_issue": get_issue,
        "create_issue": council_create_issue,
        "close_issue": close_issue,
        "report_progress": council_report_progress,
        "full_sync": full_sync,
        "generate_roadmap": generate_github_roadmap,
    }
