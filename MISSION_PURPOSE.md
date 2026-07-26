# Mission & Purpose

## Objective

Fully autonomous, self-learning, self-sustaining, self-coding, self-evolving agent council that improves itself over time and acts as a proactive personal companion.

## Pillars

### 1. Recursive Self-Evolution
- Gap analysis → implement → validate → promote/rollback
- Continuous improvement through mutation cycles
- Evaluation-gated promotion ensures quality

### 2. Autonomous Resource Optimization
- Prefer free-tier inference and zero-cost operations
- Cloud-first with weighted round-robin across providers
- Automatic failover and cooldown management
- Local models optional (Ollama) for offline capability

### 3. Model Agnosticism
- Many providers supported (20+ cloud providers)
- Failover and round-robin load balancing
- Provider health tracking and automatic recovery
- No hard dependency on any single provider

### 4. Durable Local State
- Goals, configs, memory, audit logs persisted
- Provider health and cooldown state maintained
- Checkpoint-based state recovery
- SQLite-based persistence for reliability

### 5. Companion Alignment
- Telegram control interface with `[COUNCIL:…]` identity
- Human steering through commands and goals
- Operator override capabilities
- Transparent progress and status reporting

## Architecture

### Cloud-First LLM Pool
- **Default**: `LLM_BACKEND=cloud` with weighted round-robin
- **Providers**: 20+ cloud providers (OpenRouter, Groq, DeepSeek, etc.)
- **Failover**: Automatic on 429 (rate limit) and errors
- **Cooldown**: Provider-specific cooldowns prevent repeated failures
- **Local**: Ollama optional for offline operation

### Agent Council
- **Autobot**: Orchestrator and security auditor
- **Alpha**: Mission alignment evaluator
- **Beta**: Feasibility evaluator and worker
- All agents use shared LLM router for cloud inference

### Governance
- Zero-trust HMAC-SHA256 messaging
- Immutable audit logs with chained hashes
- Consensus voting for mutations
- Autonomy levels (SAFE/LIMITED/FULL)

## Success Criteria

- System runs autonomously for 24+ hours
- Self-improves through validated mutations
- Maintains operator control via Telegram
- Optimizes resource usage (prefers free-tier)
- Recovers from provider failures automatically
- Persists state across restarts

## Operator Interface

Telegram commands:
- `/who` - Prove identity (PID, uptime)
- `/status` - Current goals, loops, mutations
- `/goal <description>` - Create a real goal
- `/approve <mutation_id>` - Approve a mutation
- `/reject <mutation_id> [reason]` - Reject a mutation
- `/stop` - Pause high-risk autonomous actions
- `/help` - Show available commands

Plain language also supported (keyword-based NLP).

## Repository

https://github.com/martinsharkey/autonomousagent
