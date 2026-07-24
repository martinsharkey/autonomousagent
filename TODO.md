# Autonomous 3-Agent Council - Project Execution Plan

**Project:** Autonomous 3-Agent Council (Autobot, Alpha, Beta)  
**Created:** 2026-07-24  
**Spec Reference:** 4 original specification files in `/autonomous agent/`  
**GitHub:** https://github.com/martinsharkey/autonomousagent

---

## 📋 Spec Refresh Protocol

**CRITICAL:** At each phase milestone, validate implementation against the original specification files:
- `DETAILED DEPLOYMENT INSTRUCTION Aut.txt` - Phase-by-phase deployment guide
- `Here is the detailed, phase-by-phas.txt` - Technology stack and model allocation details
- `Please note that the BUILD PRIORITY.txt` - Enhanced build instruction roadmap
- `To build your autonomous 3-agent co.txt` - Directory structure and code implementations

**Validation Checklist (Run at each phase completion):**
- [ ] Verify model allocations match spec (Qwen3.5:4b, Phi-4 Mini, DeepSeek Coder 1.3B)
- [ ] Confirm hardware constraints are enforced (OLLAMA_MAX_LOADED_MODELS=1, OLLAMA_CTX_SIZE=2048)
- [ ] Validate state machine includes TTL circuit breaker (loop_count >= 5)
- [ ] Ensure SAGA pattern rollbacks are implemented
- [ ] Check semantic cache prevents duplicate tool invocations
- [ ] Verify Layered Governance Architecture (LGA) layers 1-4 are in place
- [ ] Confirm zero-trust HMAC-SHA256 authentication between agents
- [ ] Validate MicroVM isolation (no Pyodide/WebAssembly for untrusted code)

---

## Phase 1: Local Bootstrapping & Cognitive Engine Setup

**Goal:** Establish local orchestrator on 8GB RAM machine with zero-cost open-weight models

### 1.1 Environment Setup
- [ ] Install Python 3.10+ and create virtual environment
- [ ] Install Visual Studio Code with Python extensions
- [ ] Install Ollama for local model serving
- [ ] Create project directory structure per spec:
  ```
  /autonomous_council
  ├── .env
  ├── requirements.txt
  ├── main.py
  ├── /core
  │   ├── state.py
  │   └── graph.py
  ├── /agents
  │   ├── autobot.py
  │   ├── alpha_evaluator.py
  │   └── beta_worker.py
  └── /tools
      ├── mcp_registry.py
      └── SKILL.md
  ```
- [ ] Create `.env` with hardware constraints:
  ```bash
  OLLAMA_MAX_LOADED_MODELS=1
  OLLAMA_NUM_PARALLEL=1
  OLLAMA_CTX_SIZE=2048
  ```
- [ ] Create `requirements.txt`:
  ```
  langgraph
  langchain
  langchain-community
  pydantic
  ollama
  python-dotenv
  ```

### 1.2 Model Deployment
- [ ] Pull Qwen3.5:4b (Q4_K_M) via Ollama (~2.5GB RAM)
- [ ] Pull Phi-4 Mini Reasoning (3.8B) via Ollama (~2.3GB RAM)
- [ ] Pull DeepSeek Coder 1.3B via Ollama (~1GB RAM)
- [ ] Verify sequential model loading (only 1 model in memory at a time)

### 1.3 Core State Implementation
- [ ] Implement `core/state.py` with `AgentState` TypedDict:
  - [ ] `messages` with `add_messages` reducer
  - [ ] `loop_count` integer for TTL circuit breaker
  - [ ] `recent_tool_invocations` for semantic cache
  - [ ] `completed_nodes` for SAGA tracking
  - [ ] `codebase_hash` for rollback reference

### 1.4 Agent Node Implementation
- [ ] Implement `agents/autobot.py` (Orchestrator Node 1):
  - [ ] Initialize ChatOllama with qwen3.5:4b
  - [ ] Implement autobot_node function
  - [ ] Add state delegation logic
- [ ] Implement `agents/alpha_evaluator.py` (Critic Node 2):
  - [ ] Initialize ChatOllama with phi4-mini
  - [ ] Implement peer-review logic
  - [ ] Add chain-of-thought validation
- [ ] Implement `agents/beta_worker.py` (Worker Node 3):
  - [ ] Initialize ChatOllama with deepseek-coder:1.3b
  - [ ] Implement rapid syntax check logic

### 1.5 SQLite Persistent Memory
- [ ] Set up SQLite with FTS5 extension
- [ ] Implement zero-ops local persistent memory
- [ ] Verify retrieval latency < 10ms
- [ ] Create memory schema for agent context

### 1.6 API Failover Router
- [ ] Implement dynamic router for cloud APIs:
  - [ ] Google AI Studio (Gemini 2.5 Flash) - 1M context
  - [ ] Groq (Llama 3.3 70B) - rapid polling (14,400 req/day)
  - [ ] OpenRouter - unified fallback gateway
- [ ] Use OpenAI-compatible API schemas
- [ ] Implement `python-dotenv` for credential injection

### 1.7 Phase 1 Validation
- [ ] **SPEC REFRESH CHECKPOINT:** Re-read all 4 specification files
- [ ] Verify model allocations match spec exactly
- [ ] Confirm hardware constraints prevent 8GB RAM exhaustion
- [ ] Test sequential model loading
- [ ] Validate state schema includes all required fields
- [ ] Document any deviations from spec in session_log.md

---

## Phase 2: State-Driven Orchestration & Fault Tolerance

**Goal:** Build cyclic state machine with fault tolerance and loop prevention

### 2.1 LangGraph State Machine
- [ ] Implement `core/graph.py` with StateGraph
- [ ] Add nodes: autobot, alpha_evaluator, beta_worker, terminal_fallback
- [ ] Configure RetryPolicy with exponential backoff:
  ```python
  local_retry = RetryPolicy(
      initial_interval=0.5,
      backoff_factor=2.0,
      max_attempts=3,
      jitter=True
  )
  ```

### 2.2 Deterministic Router
- [ ] Implement `deterministic_router` function:
  - [ ] TTL circuit breaker (loop_count >= 5 → terminal_fallback)
  - [ ] Route to beta_worker on "EXECUTE_CODE"
  - [ ] Route to alpha_evaluator on "REVIEW_REQUIRED"
  - [ ] Route to END on "CONSENSUS_REACHED"
  - [ ] Default route to autobot
- [ ] Ensure router is Python-native (immune to LLM hallucinations)

### 2.3 Conditional Edges
- [ ] Add conditional edges from autobot to all nodes
- [ ] Add edges from beta_worker → autobot
- [ ] Add edges from alpha_evaluator → autobot
- [ ] Compile graph with checkpointer

### 2.4 SAGA Pattern Rollbacks
- [ ] Implement error_handler node
- [ ] Configure atomic rollbacks for multi-step failures
- [ ] Track completed_nodes for rollback reference
- [ ] Implement file system rollback to last stable state

### 2.5 Semantic Cache
- [ ] Implement cache of recent tool invocations
- [ ] Before tool execution, check for exact duplicate (same tool + same args)
- [ ] Intercept duplicates with override prompt:
  ```
  "SYSTEM OVERRIDE: YOU HAVE ALREADY TRIED THIS ACTION AND IT FAILED."
  ```
- [ ] Update recent_tool_invocations in state

### 2.6 Reasoning Snapshots
- [ ] Implement snapshot mechanism at handoff points
- [ ] Capture agent's internal reasoning state
- [ ] Detect semantic loops (same approach with different inputs)
- [ ] Log snapshots for debugging

### 2.7 Memory Persistence
- [ ] Implement MemorySaver or SQLiteSaver
- [ ] Configure thread_id for session tracking
- [ ] Test state persistence across interruptions

### 2.8 Phase 2 Validation
- [ ] **SPEC REFRESH CHECKPOINT:** Re-read all 4 specification files
- [ ] Verify loop_count TTL prevents infinite loops
- [ ] Test RetryPolicy with simulated API timeouts
- [ ] Validate SAGA rollbacks work correctly
- [ ] Confirm semantic cache blocks duplicate invocations
- [ ] Test reasoning snapshots capture handoff context
- [ ] Document any deviations from spec in session_log.md

---

## Phase 3: Dynamic Tool Expansion via MCP

**Goal:** Enable autonomous tool creation, discovery, and execution

### 3.1 MCP Server Setup
- [ ] Install Model Context Protocol dependencies
- [ ] Set up MCP server using JSON-RPC 2.0
- [ ] Configure IPC or stdio for sandbox communication
- [ ] Test basic tool registration

### 3.2 Base Tool Implementation
- [ ] Implement `tools/mcp_registry.py` with base tools:
  - [ ] `editor(filepath, code)` - creates/modifies tool files
  - [ ] `load_tool(filepath)` - dynamically loads tools at runtime
  - [ ] `shell_exec(command)` - executes commands in isolated environment
- [ ] Add tool decorators and schema definitions

### 3.3 Progressive Tool Discovery (3-Layer System)
- [ ] Layer 1 - Catalog: Implement `search_tools` meta-tool
  - [ ] Query vector index of available capabilities
  - [ ] Return only names and brief descriptions
- [ ] Layer 2 - Inspect: Implement schema fetch
  - [ ] Retrieve full JSON schema for specific tool
  - [ ] Load schema on-demand (not all at once)
- [ ] Layer 3 - Execute: Implement tool invocation
  - [ ] Execute tool with validated parameters
  - [ ] Return results to agent

### 3.4 Code Mode (Programmatic Tool Calling)
- [ ] Implement code generation for multi-tool workflows
- [ ] Agent writes single Python/JS script
- [ ] Sandbox executes script
- [ ] Script interacts with MCP tools locally
- [ ] Return only final `console.log` summary to LLM
- [ ] Save thousands of tokens vs sequential JSON bouncing

### 3.5 Agent Skills (SKILL.md)
- [ ] Create `tools/SKILL.md` with portable markdown instructions
- [ ] Document tool design patterns
- [ ] Include examples of tool creation
- [ ] Specify tool schema format

### 3.6 Vector Similarity Search
- [ ] Implement vector indexing for tool discovery
- [ ] Use SQLite FTS5 for zero-cost vector search
- [ ] Index tool names, descriptions, and schemas
- [ ] Optimize for < 10ms retrieval

### 3.7 Phase 3 Validation
- [ ] **SPEC REFRESH CHECKPOINT:** Re-read all 4 specification files
- [ ] Verify progressive discovery prevents context overflow
- [ ] Test code mode saves tokens vs JSON mode
- [ ] Validate dynamic tool loading works at runtime
- [ ] Confirm SKILL.md enables autonomous tool creation
- [ ] Document any deviations from spec in session_log.md

---

## Phase 4: Secure MicroVM Sandboxing & Grid Spawning

**Goal:** Isolate untrusted code execution and spawn ephemeral cloud workers

### 4.1 MicroVM Isolation (Layer 1)
- [ ] **CRITICAL:** Do NOT use Pyodide or WebAssembly (vulnerable to class-hierarchy traversal)
- [ ] Set up Docker with kernel-level isolation
- [ ] Configure Firecracker MicroVMs or gVisor
- [ ] Options:
  - [ ] Northflank (Kata Containers/gVisor)
  - [ ] E2B (Firecracker MicroVMs)
  - [ ] Modal (Firecracker MicroVMs)
- [ ] Test sandbox escape prevention

### 4.2 SnapDeploy Integration
- [ ] Create Dockerfiles for worker bots
- [ ] Implement automated deployment to SnapDeploy
- [ ] Configure 10 free deploys/day utilization
- [ ] Set up auto-sleep and auto-wake functionality
- [ ] Implement Git-push CI/CD webhooks

### 4.3 Heartbeat Wake-Up Protocol
- [ ] Implement peer-to-peer HTTP ping system
- [ ] Wake dormant containers before task delegation
- [ ] Handle 15-minute inactivity timeout on free platforms
- [ ] Test wake-up latency and reliability

### 4.4 Cloud Worker Spawning
- [ ] Implement programmatic Dockerfile generation
- [ ] Deploy menial worker bots to SnapDeploy
- [ ] Configure worker bot models (DeepSeek Coder 1.3B or cloud API failovers)
- [ ] Implement task delegation protocol

### 4.5 Secondary Hosting
- [ ] Set up Cloudflare Pages for static dashboard
- [ ] Configure Render for secondary background listeners
- [ ] Implement monitoring and alerting

### 4.6 Phase 4 Validation
- [ ] **SPEC REFRESH CHECKPOINT:** Re-read all 4 specification files
- [ ] Verify NO WebAssembly/Pyodide used for untrusted code
- [ ] Test MicroVM isolation prevents host escapes
- [ ] Validate SnapDeploy auto-sleep/wake works
- [ ] Confirm heartbeat protocol wakes containers reliably
- [ ] Document any deviations from spec in session_log.md

---

## Phase 5: Layered Governance Architecture (LGA) & Consensus

**Goal:** Implement 4-layer security and decentralized consensus protocol

### 5.1 Staggered Sequential Rollout
- [ ] Configure 3-node grid for sequential mutation
- [ ] Node 1 mutates while Nodes 2 and 3 run stable code
- [ ] Implement rollback to last stable hash `C[k-1]` on crash
- [ ] Test staggered rollout with simulated failures

### 5.2 Layer 2: Intent Verification
- [ ] Implement local LLM "Judge" for high-risk tool interception
- [ ] Cascade routing: Qwen3.5-9B → Qwen2.5-14B → GPT-4o-mini
- [ ] Judge evaluates semantic consistency against core directive
- [ ] Output explicit `ALLOW` or `BLOCK` decision
- [ ] Target ~95% interception rate with low false positives

### 5.3 Layer 3: Zero-Trust Inter-Agent Protocol
- [ ] Implement HMAC-SHA256 cryptography for payload signing
- [ ] Sign all state payloads between 3 agents
- [ ] Implement strict JSON schema validation
- [ ] Prevent lateral RAG poisoning and prompt injection
- [ ] Authenticate spawned cloud workers

### 5.4 Layer 4: Immutable Audit Log
- [ ] Implement append-only log using local `fsync`
- [ ] Log every tool invocation
- [ ] Log every consensus vote
- [ ] Log every state change
- [ ] Ensure tamper-evident forensic trail

### 5.5 Consensus Mechanism
- [ ] Implement 3-agent consensus protocol
- [ ] Define consensus rules for code acceptance
- [ ] Handle dissent and disagreement
- [ ] Implement voting mechanism

### 5.6 Phase 5 Validation
- [ ] **SPEC REFRESH CHECKPOINT:** Re-read all 4 specification files
- [ ] Verify staggered rollout prevents simultaneous crashes
- [ ] Test intent verification blocks malicious actions
- [ ] Validate HMAC signatures prevent payload tampering
- [ ] Confirm audit log is immutable and tamper-evident
- [ ] Document any deviations from spec in session_log.md

---

## Final Integration & Testing

### Integration Testing
- [ ] Run full 3-agent council end-to-end
- [ ] Test all 5 phases working together
- [ ] Validate fault tolerance under stress
- [ ] Test rollback mechanisms
- [ ] Verify zero-cost operation (no unexpected API calls)

### Performance Testing
- [ ] Monitor RAM usage (must stay under 8GB)
- [ ] Measure retrieval latency (must be < 10ms)
- [ ] Test loop prevention (must terminate after 5 cycles)
- [ ] Validate semantic cache effectiveness

### Security Testing
- [ ] Attempt sandbox escapes
- [ ] Test prompt injection attacks
- [ ] Verify HMAC signature validation
- [ ] Test lateral movement prevention

### Documentation
- [ ] Create README.md with setup instructions
- [ ] Document all API endpoints
- [ ] Create architecture diagrams
- [ ] Write deployment guide

---

## Spec Refresh Log

| Date | Phase | Files Reviewed | Deviations Found | Notes |
|------|-------|----------------|------------------|-------|
| 2026-07-24 | Planning | All 4 files | None | Initial plan created |
| | | | | |
| | | | | |

---

## Notes

- **Priority:** Zero-cost resources first, cloud APIs only as failover
- **Hardware Constraint:** 8GB RAM maximum - never exceed
- **Security:** MicroVM isolation mandatory for untrusted code
- **Governance:** All 4 LGA layers must be implemented
- **Spec Compliance:** Refresh direction against original 4 files at each phase completion
