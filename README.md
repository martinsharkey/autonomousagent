# Autonomous 3-Agent Council

A zero-cost, local multi-agent system with three specialized agents (Orchestrator, Evaluator, Worker) that collaborate through a LangGraph state machine with 4-layer governance architecture.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Autonomous Council                         │
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

4. **Run the full system:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   python main.py
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
│   └── heartbeat.py               # Container wake-up protocol
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
│   └── consensus.py               # Staggered rollout & consensus
├── tests/                         # Unit and integration tests
│   ├── test_state.py              # State machine tests
│   ├── test_graph.py              # Graph routing tests
│   └── test_governance.py         # Governance layer tests
├── .github/workflows/             # CI/CD
│   └── tests.yml                  # GitHub Actions workflow
├── main.py                        # Entry point
├── requirements.txt               # Pinned dependencies
├── setup.ps1                      # Windows setup script
├── start-local.ps1                # Safe mode demo launcher
├── .env.example                   # Environment template
└── README.md                      # This file
```

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
