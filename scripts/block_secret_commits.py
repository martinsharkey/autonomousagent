#!/usr/bin/env python3
"""Pre-commit hook: block accidental commits of secret files."""
import sys
import subprocess

BLOCKED_PATTERNS = [
    ".env",
    ".env.local",
    "secrets/",
    "*.key",
    "*.pem",
    "id_rsa",
    "id_ed25519",
]

def main():
    try:
        output = subprocess.check_output(["git", "diff", "--cached", "--name-only"], text=True)
    except subprocess.CalledProcessError:
        return 0

    staged = [line.strip() for line in output.splitlines() if line.strip()]
    blocked = []
    for path in staged:
        for pattern in BLOCKED_PATTERNS:
            if pattern.endswith("/"):
                if path.startswith(pattern):
                    blocked.append(path)
                    break
            elif path == pattern or path.endswith(pattern):
                blocked.append(path)
                break

    if blocked:
        print("BLOCKED: attempted to commit secret files:")
        for path in blocked:
            print(f"  - {path}")
        print("If this is intentional, remove this hook or use --no-verify.")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
