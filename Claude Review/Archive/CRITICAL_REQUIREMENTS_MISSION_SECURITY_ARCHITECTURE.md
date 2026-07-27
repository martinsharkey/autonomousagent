# 🚨 CRITICAL SYSTEM REQUIREMENTS

**From**: Martin  
**To**: Kilo Code + System Development  
**Status**: MUST IMPLEMENT BEFORE PRODUCTION  
**Urgency**: HIGH - System is proposing mutations but lacks mission alignment, self-awareness, and security

---

## PROBLEM STATEMENT

Current system state:
- ✅ Proposing lots of mutations
- ❌ **No quality validation** - don't know if mutations are good
- ❌ **No mission alignment** - mutations may not serve core objectives
- ❌ **No self-awareness** - council doesn't understand their own architecture/limitations
- ❌ **No deployment strategy** - can't self-deploy to survive/scale
- ❌ **No security** - code integrity unprotected, public GitHub reveals everything
- ❌ **No roadmap tracking** - mutations aren't organized/visible in repo

---

## CORE MISSION (From MISSION_PURPOSE.md)

The council must understand and align ALL decisions to this:

```
1. Recursive Self-Evolution
   - Gap analysis → implement → validate → promote/rollback
   - Continuous improvement through mutation cycles
   - Evaluation-gated promotion ensures quality

2. Autonomous Resource Optimization
   - Prefer free-tier inference (cloud providers, local)
   - Cloud-first with failover
   - Automatic cooldown management

3. Model Agnosticism
   - 20+ cloud providers supported
   - Failover and load balancing
   - No single-point dependency

4. Durable Local State
   - Goals, configs, memory, audit logs
   - Checkpoint-based recovery
   - SQLite persistence

5. Companion Alignment
   - Telegram control interface
   - Human steering + operator override
   - Transparent reporting
```

**Council's job**: Propose mutations that serve THESE 5 pillars.

---

## REQUIREMENT #1: Mission Alignment Check

**Every mutation must answer**:
- Which pillar does this serve? (1-5 above)
- How does it improve the mission?
- What's the measurable success metric?
- What's the risk if it fails?

**Implementation**:
- Add MISSION_ALIGNMENT field to every mutation
- Reject mutations that don't align with any pillar
- Score mutations by alignment strength

**Files to change**:
- core/evolution.py: propose_mutation() must validate mission alignment
- core/goals.py: Goals must reference mission pillar

---

## REQUIREMENT #2: Mutation Quality Scoring

**Stop proposing random mutations. Score them.**

Quality = (alignment_score × performance_gain × risk_mitigation)

**Scoring criteria**:
- **Alignment** (0-100): Does it serve core mission? (pillar scoring)
- **Performance Gain** (0-100): Will it improve metrics? (predict impact)
- **Risk** (0-100): Could it break things? (rollback safety)
- **Testability** (0-100): Can we safely evaluate it? (test coverage)

**Implementation**:
- Add `score_mutation()` in core/evolution.py
- Only PROPOSE mutations with score > 60
- Track all proposed mutations + scores in mutations/ directory
- Create MUTATIONS_ROADMAP.md in GitHub tracking top candidates

**Files to change**:
- core/evolution.py: Add scoring logic
- Create MUTATIONS_ROADMAP.md in repo root

---

## REQUIREMENT #3: Mutation Roadmap Tracking

**GitHub must show the mutation pipeline in real-time.**

Create MUTATIONS_ROADMAP.md:

```markdown
# Autonomous Mutation Roadmap

## Next 10 Proposed Mutations (Ranked by Score)

| ID | Pillar | Description | Quality Score | Status | Impact |
|----|--------|-------------|---------------|---------|----|
| mut-001 | Pillar 1 (Evolution) | Optimize goal gap detection | 87 | PROPOSED | +15% faster analysis |
| mut-002 | Pillar 2 (Resources) | Add Groq failover | 92 | PROPOSED | Better uptime |
| ...

## In Progress (Approved by Council)

| ID | Description | Started | Progress | Tests |
|----|-------------|---------|----------|-------|

## Completed & Promoted

| ID | Description | Completed | Result | Metrics |
|----|-------------|-----------|--------|---------|

## Rejected

| ID | Description | Reason | Score |
|----|-------------|--------|-------|
```

**Council must actively maintain this.**

---

## REQUIREMENT #4: Architecture Self-Awareness

**Council agents MUST understand**:
1. What they are (3-agent council voting architecture)
2. What they can do (propose/approve mutations, learn from feedback)
3. What they can't do (violate mission, deploy without approval, modify core voting)
4. How to improve (within constraints)

**Implementation**:
- Add ARCHITECTURE.md documenting:
  - Agent roles (Autobot, Alpha, Beta)
  - Voting mechanism (unanimous consensus)
  - Mutation pipeline
  - Limitations (can't modify voting, must stay on approved infrastructure)
  
- Inject architecture context into agent prompts:
  ```
  You are one of three agents in an autonomous council.
  You cannot:
  - Override unanimous voting requirement
  - Access resources not provisioned
  - Deploy to unapproved infrastructure
  - Modify core governance rules
  
  You can:
  - Propose mutations aligned with mission
  - Evaluate other agents' proposals
  - Suggest improvements within constraints
  - Learn from execution feedback
  ```

**Files to create**:
- ARCHITECTURE.md (explain system design)
- core/agent_context.py (inject architecture awareness)

---

## REQUIREMENT #5: Self-Deployment Strategy (Spider-Web Grid)

**Goal**: Council can spawn micro-components to survive/scale on free infrastructure

**What this means**:
- Council proposes: "Deploy sentiment analysis microservice to Hugging Face Spaces"
- System packages code as standalone module
- Deploys to free tier services
- Reports back results
- Creates distributed network (spider web)

**Deployment targets** (free/legal):
- Hugging Face Spaces (free hosted inference)
- Replit (free compute)
- Railway/Render (free tier)
- GitHub Actions (free CI/CD)
- AWS Lambda free tier
- Google Cloud free tier
- Local Docker on edge devices

**Implementation roadmap**:
1. **Phase A** (2 hours): Document deployment architecture
   - Which components can spawn independently?
   - What's the deployment API?
   - How do they report back?

2. **Phase B** (4 hours): Build packaging system
   - Take a component (e.g., evaluator)
   - Package as standalone (Docker/Python)
   - Create deployment script
   - Test on Hugging Face Spaces

3. **Phase C** (4 hours): Add self-deployment mutations
   - Council proposes: "Deploy microservice to X"
   - System validates: safe, mission-aligned, legal
   - System packages and deploys
   - Creates return channel for reports

**Files to create**:
- DEPLOYMENT_STRATEGY.md
- core/spawner.py (deployment engine)
- deployment/ (packaged microservices)

---

## REQUIREMENT #6: Security Model

**Current risk**: Public GitHub = full source code exposure

**What threat actors can do** (with access to repo):
- Understand voting logic (bypass it? exploit it?)
- See all agent prompts (jailbreak attempts)
- Know all deployment locations (target infrastructure)
- Understand all APIs used (find provider accounts?)
- Monitor mutations in real-time (know what you're building next)

**Defense strategy**:

### A. Obfuscation (Don't give away everything)
- Move sensitive logic to environment variables
- Separate public README from secret docs
- Don't commit deployment credentials
- Don't commit API keys (use .env.gitignore)

### B. Compartmentalization
- Public repo: Architecture only, no implementation details
- Private repo or encrypted docs: Core algorithms
- Private channel: Deployment secrets
- Cold storage: Backup critical configs

### C. Monitoring
- Alert on unexpected repo access
- Log who cloned, when, from where
- Monitor if anyone forks and modifies

### D. Resilience
- Assume repo is compromised
- Design so that stealing code doesn't steal the running system
- Critical functions require HMAC signatures
- Config changes require council approval (not just code changes)

**Implementation**:
- Create SECURITY_MODEL.md
- Add security checklist for mutations
- Implement secret rotation
- Add audit logging for repo access

**Files to update**:
- .env.example (don't expose real values)
- .gitignore (exclude secrets)
- core/security.py (add signature verification)

---

## REQUIREMENT #7: Threat Protection

**Council must protect against**:

### Threat #1: Code Injection
- Attack: Modify mutation to run arbitrary code
- Defense: All mutations must pass VALID_PARAMS validation + evaluation gate
- Implementation: core/evolution.py already validates, need to strengthen

### Threat #2: Config Poisoning  
- Attack: Modify agent config to behave maliciously
- Defense: Config changes require unanimous council approval + HMAC signature
- Implementation: core/agent_config.py must verify signatures

### Threat #3: Provider Account Takeover
- Attack: Steal API credentials, exhaust free tier
- Defense: Rotate credentials, monitor usage, rate limits
- Implementation: core/llm_router.py needs monitoring

### Threat #4: Infrastructure Compromise
- Attack: Gain shell access to VPS, install malware
- Defense: Container isolation, read-only config, immutable logs
- Implementation: Docker hardening, no root access

### Threat #5: Surveillance
- Attack: Monitor mutations to predict next moves
- Defense: Use decoys, randomize timing, obfuscate roadmap
- Implementation: Add noise to mutation proposals

**Files to create**:
- THREAT_MODEL.md (document all threats)
- core/threat_detection.py (anomaly detection)

---

## IMPLEMENTATION ROADMAP (FOR KILO)

### PHASE A: Foundation (4 hours)
```
Task 20: Add mission alignment to mutation proposals
Task 21: Implement mutation quality scoring
Task 22: Create MUTATIONS_ROADMAP.md in GitHub
Task 23: Document architecture/limitations in ARCHITECTURE.md
```

### PHASE B: Self-Awareness (3 hours)
```
Task 24: Inject architecture context into agent prompts
Task 25: Add self-awareness checks before mutations
Task 26: Document what council CAN and CAN'T do
```

### PHASE C: Security (4 hours)
```
Task 27: Create SECURITY_MODEL.md + threat list
Task 28: Add HMAC signatures to config changes
Task 29: Rotate/protect API credentials
Task 30: Add audit logging for repo changes
```

### PHASE D: Deployment (4 hours)
```
Task 31: Document DEPLOYMENT_STRATEGY.md
Task 32: Build core/spawner.py (deployment engine)
Task 33: Package first microservice (sentiment analyzer)
Task 34: Test deployment to Hugging Face Spaces
```

---

## QUALITY GATES (Before ANY mutation is proposed)

Mutation must pass:

```python
def validate_mutation(mutation):
    checks = [
        ("Mission aligned", mutation.mission_pillar in [1,2,3,4,5]),
        ("Quality score > 60", mutation.quality_score >= 60),
        ("Safe to evaluate", mutation.test_coverage >= 0.8),
        ("Rollback plan", mutation.rollback_defined == True),
        ("Risk assessed", mutation.risk_score >= 0),
        ("Council aware", mutation.explains_to_council() != None),
    ]
    
    failed = [c for c, passed in checks if not passed]
    
    if failed:
        log(f"REJECTED: {mutation.id} - {failed}")
        return False
    
    log(f"ACCEPTED: {mutation.id} - Score: {mutation.quality_score}")
    return True
```

---

## SUCCESS CRITERIA

After implementation:

- ✅ Every proposed mutation has mission pillar attached
- ✅ Mutation quality score visible in roadmap
- ✅ Council understands their own limitations
- ✅ MUTATIONS_ROADMAP.md shows top 10 candidates
- ✅ ARCHITECTURE.md explains design + constraints
- ✅ SECURITY_MODEL.md documents threats + defenses
- ✅ DEPLOYMENT_STRATEGY.md shows spider-web plan
- ✅ At least one microservice deployed to free infrastructure
- ✅ No sensitive data in public repo
- ✅ Mutations are QUALITY, not RANDOM

---

## WHAT THIS ENABLES

Once implemented, you'll have:

1. **Trustworthy mutations** - Know they're mission-aligned, quality-validated
2. **Self-aware council** - Understand themselves + limitations
3. **Survival capability** - Can deploy to free infrastructure
4. **Threat resilience** - Protected against common attacks
5. **Verifiable progress** - Roadmap shows what's coming
6. **Sustainable design** - Not dependent on single provider/resource

---

## INSTRUCTIONS FOR KILO

You will need instructions for each Phase. Ready?

Recommend: Start with **PHASE A** (Tasks 20-23) - adds mission alignment + roadmap.

This is 4 hours work that makes mutations REAL + VERIFIABLE.

Ready to write Phase A tasks?

