"""Council Git Identity — ensures all autonomous commits are distinguishable.

All git commits made by the council daemon use a distinct author identity
so the operator can differentiate between:
- Human commits (the operator)
- Kilo Code / other agentic devs (tools using operator's git config)
- Council autonomous commits (this identity)

Usage:
    from core.council_git_identity import council_commit_args
    subprocess.run(["git", "commit"] + council_commit_args(message), ...)
"""

# The council's unique git identity
COUNCIL_AUTHOR_NAME = "Council Daemon"
COUNCIL_AUTHOR_EMAIL = "council-daemon@autonomousagent.local"
COUNCIL_AUTHOR = f"{COUNCIL_AUTHOR_NAME} <{COUNCIL_AUTHOR_EMAIL}>"

# Tag appended to commit messages for easy grep
COUNCIL_COMMIT_TAG = "[council-daemon]"


def council_commit_args(message: str) -> list:
    """Return git commit args with council identity and tagged message.
    
    Usage:
        subprocess.run(["git", "commit"] + council_commit_args("feat: thing"), ...)
    """
    tagged_message = f"{message} {COUNCIL_COMMIT_TAG}" if COUNCIL_COMMIT_TAG not in message else message
    return [
        "--author", COUNCIL_AUTHOR,
        "-m", tagged_message,
    ]
