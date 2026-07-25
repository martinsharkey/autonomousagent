# Autonomous 3-Agent Council

A zero-cost, local multi-agent system with three specialized agents (Orchestrator, Evaluator, Worker) that collaborate through a LangGraph state machine with 4-layer governance architecture.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Autonomous Council                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 6: Learning & Communication                           │
│  ├─ Inter-Agent Message Bus (HMAC-signed)                    │
│  ├─ Trajectory Logger (state, prompts, responses, rewards)   │
│  ├─ Learning Engine (pattern extraction, feedback)           │
│  └─ Offline Training Pipeline                                │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: Governance (LGA)                                    │
│  ├─ L1: MicroVM Sandboxing                                   │
│  ├─ L2: Intent Verification (LLM Judge)                      │
│  ├─ L3: Zero-Trust Protocol (HMAC-SHA256)                    │
│  └─ L4: Immutable Audit Log                                  │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: Dynamic Tools (MCP)                                │
│  ├─ Progressive Discovery (3-layer)                          │
│  ├─ Code Mode (programmatic calling)                         │
│  └─ Runtime Tool Registration                                │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: State Orchestration (LangGraph)                    │
│  ├─ TTL Circuit Breaker (loop_count >= 5)                    │
│  ├─ Semantic Cache (duplicate prevention)                    │
│  ├─ SAGA Rollbacks (atomic recovery)                         │
│  └─ Reasoning Snapshots (handoff tracking)                   │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Agent Nodes                                        │
│  ├─ Autobot (Orchestrator) - Qwen3.5:4b                     │
│  ├─ Alpha (Evaluator) - Phi-4 Mini                          │
│  └─ Beta (Worker) - DeepSeek Coder 1.3B                     │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Infrastructure                                     │
│  ├─ Ollama (local LLM serving)                               │
│  ├─ SQLite FTS5 (persistent memory)                          │
│  └─ API Router (cloud failover)                              │
└─────────────────────────────────────────────────────────────┘
```

## Active Council Demo - Communication & Learning

The council members actively communicate with each other through a secure message bus, capture trajectories for learning, and continuously improve their performance.

### Running the Active Council Demo

```powershell
python demo_active_council.py
```

This demo demonstrates:
1. **Inter-Agent Communication**: Agents send signed messages to coordinate tasks
2. **Trajectory Capture**: All interactions are logged with rewards
3. **Learning from Experience**: The learning engine analyzes patterns and provides feedback
4. **Continuous Improvement**: Agents learn from successful and failed trajectories

### Demo Output

```
======================================================================
ACTIVE COUNCIL DEMO - Inter-Agent Communication & Learning
======================================================================

[PHASE 1] Demonstrating Inter-Agent Communication
----------------------------------------------------------------------

1. Autobot broadcasts task initialization to all agents...
2. Beta Worker responds with implementation plan...
3. Alpha Evaluator reviews the plan and provides feedback...
4. Beta Worker acknowledges and incorporates feedback...
5. Autobot coordinates final consensus...

Communication Statistics:
  Total messages: 5
  Messages by type: {'task_init': 1, 'implementation_plan': 1, ...}

[PHASE 2] Capturing Agent Trajectories
----------------------------------------------------------------------

Total trajectories captured: 10
  autobot: 4 trajectories, avg reward: 0.88
  alpha_evaluator: 2 trajectories, avg reward: 0.88
  beta_worker: 4 trajectories, avg reward: 0.85

[PHASE 3] Learning from Trajectories
----------------------------------------------------------------------

[AUTOBOT]
  Total trajectories: 4
  Successful: 3
  Failed: 1
  Patterns detected: 2
  Recommendations:
    - Good performance: 3 successful vs 1 failed trajectories
    - Strong pattern detected: Coordinate web scraper... (avg reward: 0.88)

[PHASE 4] Learning Summary & Insights
----------------------------------------------------------------------

Overall Learning Statistics:
  Total sessions learned: 1
  Total patterns extracted: 6
  Total recommendations generated: 9
```

### Key Features

**Inter-Agent Communication** (`core/communication.py`):
- Secure message bus with HMAC-SHA256 signatures
- Message types: requests, responses, broadcasts, feedback
- Message persistence and audit logging
- Real-time message delivery with inboxes

**Trajectory Capture** (`core/data_logger.py`):
- Logs agent states, prompts, responses, and rewards
- Session-based organization
- Export for training data
- Filtering by reward threshold

**Learning Engine** (`core/learning.py`):
- Pattern extraction from successful trajectories
- Recommendation generation for improvement
- Feedback delivery via message bus
- Session-based learning summaries

**Offline Training** (`training/retrain.py`):
- Train agents from captured trajectories
- Filter by reward threshold
- Model versioning and registry
- Gated deployment with governance checks

**Model Deployment** (`deploy/deploy_model.py`):
- Governance-gated deployment
- Model validation and verification
- Rollback capabilities
- Deployment history tracking

## Quickstart (Safe Mode - No Code Execution)

This mode runs the state machine with mock agents, demonstrating the orchestration flow without executing any generated code.

### Prerequisites

- **Windows 10/11** (PowerShell 5.1+)
- **Python 3.10+** ([Download](https://www.python.org/downloads/))
- **Git** ([Download](https://git-scm.com/downloads))
- **8GB RAM minimum** (16GB recommended)

### Installation

1. **Clone the repository:**
   ```powershell
   git clone https://github.com/martinsharkey/autonomousagent.git
   cd autonomousagent
   ```

2. **Run the setup script:**
   ```powershell
   .\setup.ps1
   ```
   This creates a virtual environment and installs dependencies.

3. **Start in safe mode:**
   ```powershell
   .\start-local.ps1
   ```
   This runs a demo flow showing state transitions without code execution.

### Expected Output

```
=== Autonomous Council - Safe Mode Demo ===
Initializing state machine...
[Autobot] Analyzing task: Write a web scraper
[Router] Decision: beta_worker
[Beta] Generating code structure
[Router] Decision: alpha_evaluator
[Alpha] Reviewing code quality
[Router] Decision: autobot
[Autobot] Consensus reached
=== Demo Complete ===
Loop count: 3
Completed nodes: ['autobot', 'beta_worker', 'alpha_evaluator']
```

## Security Requirements

Before running in production, you must configure required secrets:

```bash
# Generate a strong HMAC secret key
export HMAC_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Configure Telegram bot (optional but recommended for operator interface)
export TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
```

**Required Environment Variables:**
- `HMAC_SECRET_KEY` - Required for audit log signing and zero-trust messaging. The system will fail to start if not set.

Generate a secure key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Full System Setup (With Local LLMs)

### Prerequisites

- **Ollama** ([Download](https://ollama.ai/download))
- **8GB RAM** (models require ~6GB total)
- **10GB disk space** (for model weights)

### Installation

1. **Install Ollama models:**
   ```powershell
   ollama pull qwen3.5:4b
   ollama pull phi4-mini
   ollama pull deepseek-coder:1.3b
   ```

2. **Verify models are loaded:**
   ```powershell
   ollama list
   ```
   Expected output:
   ```
   NAME                    ID              SIZE    MODIFIED
   qwen3.5:4b              ...             2.5 GB  ...
   phi4-mini               ...             2.3 GB  ...
   deepseek-coder:1.3b     ...             1.0 GB  ...
   ```

3. **Configure environment:**
   ```powershell
   Copy-Item .env.example .env
   ```
   Edit `.env` to add API keys (optional, for cloud failover):
   ```env
   OLLAMA_MAX_LOADED_MODELS=1
   OLLAMA_NUM_PARALLEL=1
   OLLAMA_CTX_SIZE=2048
   
   # Optional: Cloud API failover
   GOOGLE_AI_STUDIO_API_KEY=your_key_here
   GROQ_API_KEY=your_key_here
   OPENROUTER_API_KEY=your_key_here
   ```

4. **Run the autonomous council (primary entry point):**
   ```powershell
   .\venv\Scripts\Activate.ps1
   python council_daemon.py --interval 60 --autonomy limited
   ```
   
   **Autonomy Levels:**
   - `safe`: No mutations, no code execution. Human approves everything.
   - `limited`: Low-risk mutations only. Human approves medium/high risk. (Default)
   - `full`: Full autonomy. Low/medium auto-approved, high requires human.

## Telegram Command Interface

The council provides a Telegram command interface for operator control. All messages from the council use the `[COUNCIL:SPEAKER]` identity prefix.

### Available Commands

- `/who` - Prove identity (returns real uptime + PID from running daemon)
- `/status` - Show current goals, loops, mutations, and autonomy level
- `/goal <description>` - Create a real goal that the daemon will execute
- `/approve <mutation_id>` - Approve a pending mutation
- `/reject <mutation_id> [reason]` - Reject a mutation with optional reason
- `/stop` - Pause high-risk autonomous actions
- `/help` - Show available commands

### Telegram Configuration

**CRITICAL:** The council uses a dedicated Telegram bot token that must NEVER be shared with Kilo Code or any other AI assistant.

1. **Configure environment:**
   ```powershell
   Copy-Item .env.example .env
   ```

2. **Edit `.env` to add Telegram credentials:**
   ```env
   # Telegram Configuration
   # IMPORTANT: Never share TELEGRAM_BOT_TOKEN with Kilo or other AI assistants
   # This token is exclusively for the autonomous council process
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   TELEGRAM_ALLOWED_USER_IDS=your_user_id_here
   ```

3. **Security Rules:**
   - TELEGRAM_BOT_TOKEN must NEVER be shared with Kilo Code or any external AI
   - Only the council daemon should have access to this token
   - If you need Kilo for coding help, use a separate bot or chat
   - All council messages use [COUNCIL:SPEAKER] prefix for identity verification

### Example Usage

```
Operator: /who
Council: [COUNCIL:DAEMON] 🤖 Council Identity Proof
         PID: 12345
         Uptime: 3600s
         I am the real council process.

Operator: /goal Write a web scraper for product data
Council: [COUNCIL:DAEMON] ✅ Goal Created
         Goal ID: abc123-def456-ghi789
         Description: Write a web scraper for product data

[Later...]
Council: [COUNCIL:DAEMON] ✅ Goal Completed
         Goal ID: abc123-def456-ghi789
         Status: completed
         Reward: 0.90
         Duration: 45.2s
```

## Project Structure

```
autonomousagent/
├── core/                          # Core orchestration
│   ├── state.py                   # AgentState TypedDict
│   ├── graph.py                   # LangGraph state machine
│   ├── memory.py                  # SQLite FTS5 persistent memory
│   ├── api_router.py              # Cloud API failover
│   ├── semantic_cache.py          # Duplicate invocation prevention
│   ├── snapshots.py               # Reasoning snapshots
│   ├── rollback.py                # SAGA pattern rollbacks
│   ├── tool_discovery.py          # Progressive tool discovery
│   ├── code_mode.py               # Programmatic tool calling
│   ├── sandbox.py                 # MicroVM sandbox execution
│   ├── snapdeploy.py              # Cloud worker spawning
│   ├── heartbeat.py               # Container wake-up protocol
│   ├── telegram.py                # Telegram bot + command listener
│   ├── goals.py                   # SQLite-based durable goal store
│   ├── agent_config.py            # Versioned agent configuration store
│   ├── evaluation.py              # Evaluation suite for gating mutations
│   ├── autonomy_levels.py         # SAFE/LIMITED/FULL autonomy control
│   ├── governor.py                # Resource governors (cycles, models, sandboxes)
│   ├── planning.py                # Agent planning and tool use
│   ├── agent_loop.py              # Continuous autonomous agent loops
│   ├── models.py                  # Single source of truth for model registry
│   ├── checkpointer.py            # SQLite-based durable checkpointer
│   └── health.py                  # Health check CLI
├── agents/                        # Agent node implementations
│   ├── autobot.py                 # Orchestrator (Qwen3.5:4b)
│   ├── alpha_evaluator.py         # Evaluator (Phi-4 Mini)
│   └── beta_worker.py             # Worker (DeepSeek Coder 1.3B)
├── tools/                         # MCP tool registry
│   ├── mcp_registry.py            # Tool registration and discovery
│   └── SKILL.md                   # Tool creation guide
├── governance/                    # 4-layer governance architecture
│   ├── zero_trust.py              # HMAC-SHA256 authentication
│   ├── intent_judge.py            # L2 intent verification
│   ├── audit_log.py               # L4 immutable audit log
│   ├── consensus.py               # Staggered rollout & consensus
│   ├── keys.py                    # Key management + rotation
│   └── rotate_keys.py             # Key rotation CLI
├── tests/                         # Unit and integration tests
│   ├── test_state.py              # State machine tests
│   ├── test_graph.py              # Graph routing tests
│   ├── test_governance.py         # Governance layer tests
│   ├── test_sandbox.py            # Sandbox isolation tests
│   ├── test_code_validator.py     # AST static analysis tests
│   ├── test_mcp_security.py       # MCP registration security tests
│   ├── test_audit_log_integrity.py # Audit log integrity tests
│   ├── test_snapshot_integrity.py # Snapshot integrity tests
│   ├── test_keys.py               # Key management tests
│   └── test_model_availability.py # Model preflight tests
├── .github/workflows/             # CI/CD
│   └── tests.yml                  # GitHub Actions workflow
├── council_daemon.py              # PRIMARY ENTRY POINT - autonomous operation
├── main.py                        # One-shot goal injection (debug mode)
├── requirements.txt               # Pinned dependencies
├── setup.ps1                      # Windows setup script
├── start-local.ps1                # Safe mode demo launcher
├── .env.example                   # Environment template
├── COPILOT_REVIEW.md              # Review findings + developer evidence
├── VERIFICATION_EVIDENCE.md       # Code verification against review claims
├── TELEGRAM_TRANSCRIPT_EVIDENCE.md # Telegram command verification
├── MUTATION_BEHAVIOR_PROOF.md     # Before/after mutation behavior proof
└── README.md                      # This file
```

## Current Limitations (Honest Assessment)

### What Works
- ✅ Telegram identity prefix [COUNCIL:SPEAKER] on all messages
- ✅ Inbound command listener (/who, /status, /goal, /approve, /reject, /stop)
- ✅ Dedicated Telegram bot token with security documentation
- ✅ Goal ID + duration in all completion messages
- ✅ All agents load active config on every entry
- ✅ Mutations create real config versions via agent_config store
- ✅ Evaluation suite gates promotion before apply
- ✅ Agent loops create/select goals from goal store
- ✅ Goals execute through graph with real rewards (not hardcoded)
- ✅ Daemon resumes open goals on startup
- ✅ Autonomy level flag (SAFE/LIMITED/FULL)
- ✅ Resource governors enforce limits
- ✅ SQLite-based durable checkpointer (state survives restarts)
- ✅ Single source of truth for model registry

### What's Documented But Not Fully Production-Ready
- ⚠️ Docker sandbox is hardened but Firecracker/gVisor migration path is documented, not implemented
- ⚠️ SnapDeploy integration exists but requires API key for actual spawning
- ⚠️ Offline training pipeline exists but requires manual execution
- ⚠️ Model deployment governance exists but requires manual approval flow

### What's Scaffolding
- 📝 Some advanced features (multi-agent spawning, distributed consensus) are designed but not fully wired
- 📝 Prometheus-style metrics export is designed but not implemented
- 📝 Full integration test suite for entire loop is designed but not complete

**Bottom Line:** The core autonomy loop is closed and working. The system can run unattended, create goals, execute them, learn from trajectories, propose mutations, evaluate them, and apply changes that measurably affect behavior. Security foundations are solid. Some advanced features need additional wiring for production use.

## Development Setup

### Running Tests

```powershell
.\venv\Scripts\Activate.ps1
pytest tests/ -v
```

### Test Coverage

```powershell
pytest tests/ --cov=core --cov=agents --cov=governance --cov-report=html
```

### Code Style

```powershell
black core/ agents/ tools/ governance/
isort core/ agents/ tools/ governance/
flake8 core/ agents/ tools/ governance/
```

## Security Considerations

### MicroVM Sandboxing

**CRITICAL:** Never run generated code on the host OS or in soft sandboxes (Pyodide/WebAssembly). These are vulnerable to class-hierarchy traversal exploits that can execute host-level commands.

**Safe execution requires:**
- Firecracker MicroVMs (E2B, Modal)
- OR gVisor/Kata Containers (Northflank)
- OR Docker with strict seccomp profiles (development only)

### Governance Layers

1. **L1 (Sandbox):** OS-level isolation via MicroVMs
2. **L2 (Intent Judge):** LLM evaluates action safety before execution
3. **L3 (Zero-Trust):** HMAC-SHA256 signed payloads between agents
4. **L4 (Audit Log):** Append-only log with fsync for forensic trail

### Resource Limits

The system enforces strict memory limits to prevent 8GB RAM exhaustion:
- `OLLAMA_MAX_LOADED_MODELS=1` (sequential loading)
- `OLLAMA_CTX_SIZE=2048` (KV cache cap)
- TTL circuit breaker (max 5 loops)

## Troubleshooting

### Ollama Models Not Loading

**Problem:** `ollama list` shows no models

**Solution:**
```powershell
ollama pull qwen3.5:4b
ollama pull phi4-mini
ollama pull deepseek-coder:1.3b
```

### Memory Exhaustion

**Problem:** System crashes or becomes unresponsive

**Solution:**
1. Verify `.env` has `OLLAMA_MAX_LOADED_MODELS=1`
2. Stop other memory-intensive applications
3. Consider using cloud API failover instead of local models

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'langgraph'`

**Solution:**
```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Port Conflicts

**Problem:** Ollama fails to start (port 11434 in use)

**Solution:**
```powershell
# Find process using port 11434
netstat -ano | findstr :11434

# Kill the process (replace PID)
taskkill /PID <PID> /F
```

## Model Specifications

| Agent | Model | RAM | Context | Purpose |
|-------|-------|-----|---------|---------|
| Autobot | Qwen3.5:4b | ~2.5GB | 256K | Orchestration, code generation |
| Alpha | Phi-4 Mini | ~2.3GB | 128K | Evaluation, peer review |
| Beta | DeepSeek Coder 1.3B | ~1.0GB | 16K | Rapid syntax checks |

**Total RAM:** ~5.8GB (sequential loading enforced)

## License

This project is provided as-is for educational and research purposes. Ensure compliance with model licenses (Qwen, Phi, DeepSeek) and cloud API terms of service.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

- **Issues:** [GitHub Issues](https://github.com/martinsharkey/autonomousagent/issues)
- **Documentation:** See `TODO.md` for implementation roadmap
- **Session Log:** See `session_log.md` for development history
