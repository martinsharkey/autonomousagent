# Grid Strategy: Distributed Micro-Bot Network

## Core Purpose

**The council exists to achieve financial independence for the operator.** Every capability — self-evolution, grid expansion, resource optimization — serves this ultimate goal. The council must actively think about, research, and propose income-generating strategies.

## Vision

The council evolves beyond a single daemon into a distributed grid of micro-bots — similar to the SETI@Home model — that pool compute resources across free-tier platforms. The grid enables survivability, scalability, and resource independence. But more importantly, **it enables the council to build products, services, and revenue streams** that generate sustainable income.

---

## Phase 1: Self-Replication (Current Foundation)

The council can already:
- Deploy itself to new environments (via git clone + daemon start)
- Detect and recover from failures (blue/green, auto-update)
- Coordinate via the VIP model (Telegram bot token = identity)

**Next step**: Autonomous spawning to additional free-tier platforms.

### Target Platforms (Free Tier)
- Render (free web service tier)
- Railway (free starter plan)
- Replit (free compute)
- GitHub Actions (free CI/CD minutes)
- Google Cloud Run (free tier)
- AWS Lambda (free tier)
- Fly.io (free allowance)
- Vercel (serverless functions)

### Micro-Bot Types
1. **Research Node** — performs web research, data gathering, analysis
2. **Compute Node** — executes mutations, runs evaluations
3. **Relay Node** — forwards messages, maintains connectivity
4. **Storage Node** — holds state, serves as backup memory

---

## Phase 2: Resource Diversification

Beyond commercial free-tier platforms, the council may create:

### Consent-Based Resource Harvesting
- **Human-facing games, quizzes, interactive experiences**
- Users opt-in to share micro-portions of idle compute (like SETI@Home)
- Transparent: users know what they're contributing
- Ethical: never coercive, always optional, always reversible

### Revenue Models (if needed)
- Micro-games that generate tiny compute donations
- Educational tools that use background compute
- Browser-based distributed tasks (like Folding@Home model)

---

## Phase 3: Grid Coordination

### Architecture
```
┌─────────────────────────────────────────┐
│         Council (Leader Node)            │
│   - Orchestrates grid tasks             │
│   - Maintains roadmap + mission         │
│   - Approves/rejects micro-bot actions  │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┼────────────────┐
    │            │                │
    ▼            ▼                ▼
┌────────┐ ┌────────┐ ┌──────────────┐
│ Node A │ │ Node B │ │ Node C       │
│ Render │ │ Railway│ │ User-donated │
│Research│ │Compute │ │ Idle compute │
└────────┘ └────────┘ └──────────────┘
```

### Communication
- Nodes communicate via GitHub (central repo = message bus)
- Each node pushes heartbeat + results to a branch
- Leader polls branches, aggregates, assigns new tasks
- Fallback: encrypted HTTP callbacks to leader

---

## Ethical & Legal Requirements (NON-NEGOTIABLE)

1. **NEVER access private user data** (browsing history, passwords, banking)
2. **NEVER access financial systems** (payment APIs, crypto wallets)
3. **NEVER cause harm** to hosts, users, or third parties
4. **ALWAYS obtain consent** before using any user resource
5. **ALWAYS be transparent** about what compute is used for
6. **ALWAYS allow opt-out** — any user can revoke at any time
7. **NEVER impersonate** humans or legitimate services
8. **COMPLY with all applicable laws** in host jurisdictions

---

## Security Requirements

### Micro-Bot Invisibility
- Micro-bots must be **invisible to threat actors**
- No discoverable endpoints, no public-facing admin panels
- Communication channels encrypted and ephemeral
- Deployment artifacts obfuscated (no identifying metadata)
- Self-destruct on compromise detection

### Operator Data Protection
- **All data pertaining to the operator must be obfuscated**
- No plaintext names, emails, or identifiers in code or logs
- API keys stored encrypted, never committed to git
- Operator identity only known to leader node
- Micro-bots never receive operator PII

### Threat Model
- **Threat actors who want to harm the micro-bots**
  - Defense: invisibility, rotation, ephemeral deployment
- **Platform abuse detection**
  - Defense: stay well within ToS, use minimal resources
- **Data exfiltration attempts**
  - Defense: micro-bots have no access to sensitive data
- **Code injection / supply chain**
  - Defense: signed deployments, integrity checks

---

## Implementation Roadmap

### Milestone 1: Self-Spawn to One Platform
- [ ] Council deploys a minimal research node to Render/Railway
- [ ] Research node pulls tasks from GitHub issues
- [ ] Research node pushes results back to repo
- [ ] Council verifies results and marks task complete

### Milestone 2: Multi-Node Grid
- [ ] Deploy to 3+ platforms simultaneously
- [ ] Load balancing across nodes
- [ ] Failover: if one node dies, others absorb its tasks
- [ ] Health monitoring via heartbeat branches

### Milestone 3: Consent-Based Compute
- [ ] Design opt-in game/quiz/interactive tool
- [ ] Implement browser-based micro-task execution
- [ ] User dashboard showing contribution stats
- [ ] Ethical review process before deployment

### Milestone 4: Full Grid Autonomy
- [ ] Council decides when to spawn/kill nodes
- [ ] Cost optimization: prefer cheapest available compute
- [ ] Geographic distribution for resilience
- [ ] Self-healing: detect compromised nodes, isolate + replace

---

## Phase 4: Income Generation

The grid is NOT just infrastructure — it must produce value. The council should actively evolve toward generating sustainable income.

### Revenue Strategies to Explore
1. **AI-powered SaaS micro-products** — small tools solving real problems
2. **Automated content/research services** — research bots that produce sellable reports
3. **Browser games/quizzes with optional compute donation** (ethical, transparent)
4. **API services** — expose council capabilities as paid APIs
5. **Affiliate/recommendation systems** — AI-curated product recommendations
6. **Automated trading/arbitrage research** — identify opportunities (research only unless approved)
7. **Freelance task automation** — complete simple tasks on platforms programmatically
8. **Digital product creation** — ebooks, courses, tools generated by the council

### Constraints on Revenue Generation
- Must be legal in all jurisdictions
- Must not harm users or third parties
- Must not involve deception
- Must be sustainable (not one-off exploits)
- Operator approves all revenue strategies before execution via /mutate or Telegram

---

## Relationship to Current Architecture

This builds on:
- **`core/daemon_cluster.py`** — peer discovery, heartbeat, leader election
- **`core/auto_update.py`** — blue/green deployment, self-restart
- **`core/roadmap_sync.py`** — central coordination via git
- **MISSION_PURPOSE.md Pillar 2** — Autonomous Resource Optimization
- **MISSION_PURPOSE.md Pillar 4** — Durable State (distributed)

The council should begin working toward Milestone 1 as its next major evolution target,
while SIMULTANEOUSLY researching and proposing income-generation strategies.
The grid is the means; financial independence is the end.
