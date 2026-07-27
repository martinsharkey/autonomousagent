# Phase B: Self-Deployment Architecture

## Objective
Enable the autonomous council to package, deploy, and manage microservices across free cloud platforms, creating a resilient spider-web grid.

## Component Boundaries

### Main Council (Stateful Manager)
- Runs on primary VPS/host
- Maintains all state: AgentState, mutations, decisions, versions
- Proposes deployments based on opportunities
- Votes on deployment mutations
- Aggregates results from microservices
- Handles learning from feedback

### Microservices (Stateless Workers)
- Run on free platforms (HF Spaces, Replit, Railway, GitHub Actions)
- Each performs a single specialized function
- Use cloud LLMs via existing `llm_router` (no local models)
- Receive tasks from queue/API
- Report results back to main council
- Report health status periodically

### Mesh Communication Layer
- HTTP-based task distribution and result reporting
- Health check endpoints on all nodes
- Node registry maintained by main council
- Dead node detection and auto-replacement

## Deployment API Spec

### Microservice Contract
```python
# Required endpoints
GET  /health                    # Health check
POST /task                      # Receive task
GET  /task/{task_id}/status     # Check task status
POST /result                    # Report result back (optional, can use callback)

# Required format
{
    "task_id": "uuid",
    "input": {...},
    "callback_url": "https://council.example.com/api/mesh/result"
}
```

### Council-to-Node Communication
```python
# Council sends task
POST https://node-platform.example.com/task
{
    "task_id": "uuid",
    "component": "sentiment_analyzer",
    "input": {"text": "analyze this"},
    "callback_url": "https://council.example.com/api/mesh/result"
}

# Node reports result
POST https://council.example.com/api/mesh/result
{
    "task_id": "uuid",
    "node_id": "hf-spaces-sentiment-001",
    "status": "completed",
    "result": {"sentiment": 0.85},
    "timestamp": "2026-07-27T10:00:00Z"
}
```

### Health Check Protocol
```python
# Node health response
GET https://node-platform.example.com/health
{
    "node_id": "hf-spaces-sentiment-001",
    "component": "sentiment_analyzer",
    "platform": "huggingface_spaces",
    "status": "healthy",
    "uptime_seconds": 3600,
    "tasks_completed": 150,
    "last_task_at": "2026-07-27T09:59:00Z",
    "quota_used_percent": 45
}
```

## Platform Support Matrix

| Platform | Packaging | Runtime | Persistence | Best For |
|----------|-----------|---------|-------------|----------|
| Hugging Face Spaces | Docker/FastAPI | CPU | 50GB | Inference |
| Replit | Python script | CPU | Project | Light tasks |
| Railway | Docker | 500h/mo | 100GB | Scheduled jobs |
| GitHub Actions | Workflow | 2000min/mo | Artifacts | CI/CD pipelines |

## Mesh Topology

```
                    ┌─────────────────┐
                    │   Main Council  │
                    │   (Stateful)    │
                    └────────┬────────┘
                             │ HTTP/Queue
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ HF Spaces│  │  Replit  │  │ Railway  │
        │ [Node 1] │  │ [Node 2] │  │ [Node 3] │
        └──────────┘  └──────────┘  └──────────┘
```

## Security Model
- All nodes authenticate with council via shared secret or token
- Callback URLs whitelisted
- Task inputs sanitized before execution
- Results validated before aggregation
- Node identities verified via HMAC signatures
