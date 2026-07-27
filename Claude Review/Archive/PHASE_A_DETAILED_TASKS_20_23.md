# PHASE A: MISSION ALIGNMENT + QUALITY SCORING + ROADMAP

**Owner**: Kilo Code  
**Duration**: 4 hours  
**Difficulty**: Moderate  
**Acceptance**: Mutations have mission scores, quality scores, and roadmap is public in GitHub  

---

## CONTEXT

Currently: System proposes mutations but nobody knows if they're good.

After Phase A: Every mutation has:
- ✅ Quality score (0-100)
- ✅ Mission alignment (Pillar 1-5)
- ✅ Risk assessment
- ✅ Testability rating
- ✅ Public roadmap in GitHub showing top candidates

---

## TASK 20: Add Mission Alignment to Mutation Proposals

**What**: Every mutation must declare which core mission pillar it serves

**Where**: `core/evolution.py`, function `propose_mutation()`

**Changes**:
1. Add MISSION_PILLARS enum:
```python
MISSION_PILLARS = {
    1: "Recursive Self-Evolution",
    2: "Autonomous Resource Optimization",
    3: "Model Agnosticism",
    4: "Durable Local State",
    5: "Companion Alignment"
}
```

2. Before proposing mutation, ask:
```python
def propose_mutation(self, agent_name, evaluation_result):
    # ... existing code ...
    
    # NEW: Determine mission pillar
    pillar = self._classify_mutation_pillar(agent_name, proposed_changes)
    
    if pillar is None:
        log(f"REJECTED: {mutation_id} - No mission alignment")
        return None  # Don't propose unaligned mutations
    
    mutation_obj["mission_pillar"] = pillar
    mutation_obj["mission_description"] = MISSION_PILLARS[pillar]
    
    # Then save mutation
```

3. Implement `_classify_mutation_pillar()`:
```python
def _classify_mutation_pillar(self, agent_name, changes):
    # Use LLM to ask: "Which pillar does this serve?"
    # Return pillar number (1-5) or None
    
    prompt = f"""
    Given these proposed parameter changes: {changes}
    Which core mission pillar do they serve?
    
    Pillars:
    1 = Recursive Self-Evolution (improve itself)
    2 = Resource Optimization (use cheaper/free resources)
    3 = Model Agnosticism (don't depend on one provider)
    4 = Durable Local State (persistence/recovery)
    5 = Companion Alignment (obey human commands)
    
    Return just the number (1-5) or "NONE" if unaligned.
    """
    
    # Ask agent (using existing LLM call)
    answer = self.agents[agent_name].decide(prompt)
    
    try:
        pillar = int(answer.strip())
        return pillar if 1 <= pillar <= 5 else None
    except:
        return None
```

**Acceptance Criteria**:
- All mutations have `mission_pillar` field (1-5)
- Mutations without pillar are rejected
- Pillar assignment is deterministic (same changes = same pillar)
- Log shows rejected mutations with reason

**Test**:
```bash
# Manually trigger mutation
# Verify proposed mutation has mission_pillar set
grep "mission_pillar" evolution_data.json
```

---

## TASK 21: Implement Mutation Quality Scoring

**What**: Score mutations 0-100 based on:
- Alignment strength
- Predicted performance gain
- Risk level
- Testability

**Where**: `core/evolution.py`, new function `score_mutation()`

**Implementation**:

```python
def score_mutation(self, mutation_obj: Dict) -> int:
    """Score a mutation 0-100. Only propose if > 60."""
    
    scores = {}
    
    # 1. ALIGNMENT SCORE (0-100)
    # How well does this serve its pillar?
    alignment = self._score_alignment(mutation_obj)  # Ask LLM
    scores["alignment"] = alignment
    
    # 2. PERFORMANCE GAIN (0-100)
    # Will it actually improve metrics?
    gain = self._estimate_performance_gain(mutation_obj)  # Historical data
    scores["performance_gain"] = gain
    
    # 3. RISK SCORE (0-100)
    # How likely to break things? (inverse: low risk = high score)
    risk = self._assess_risk(mutation_obj)  # Ask LLM
    scores["risk"] = 100 - risk  # Invert: high safety = high score
    
    # 4. TESTABILITY (0-100)
    # Can we safely evaluate it?
    testability = self._rate_testability(mutation_obj)  # Ask LLM
    scores["testability"] = testability
    
    # Weighted average
    # Alignment: 40%, Performance: 30%, Risk: 20%, Testability: 10%
    final_score = int(
        scores["alignment"] * 0.40 +
        scores["performance_gain"] * 0.30 +
        scores["risk"] * 0.20 +
        scores["testability"] * 0.10
    )
    
    mutation_obj["quality_score"] = final_score
    mutation_obj["quality_breakdown"] = scores
    
    return final_score
```

**Scoring helper methods**:

```python
def _score_alignment(self, mutation: Dict) -> int:
    """How well does this serve its mission pillar?"""
    
    pillar = mutation.get("mission_pillar")
    changes = mutation.get("proposed_changes", {})
    
    prompt = f"""
    Pillar: {MISSION_PILLARS.get(pillar)}
    Changes: {changes}
    
    Score 0-100: How well does this mutation serve the pillar?
    0 = Doesn't help at all
    100 = Perfectly aligned and impactful
    
    Return just the number.
    """
    
    score = self._ask_agent_for_score(prompt)
    return max(0, min(100, score))

def _estimate_performance_gain(self, mutation: Dict) -> int:
    """Will it improve metrics?"""
    
    # Look at similar past mutations
    past_similar = self.find_similar_mutations(mutation)
    
    if not past_similar:
        return 50  # Unknown = neutral
    
    improvements = [m.get("actual_gain", 0) for m in past_similar]
    avg_gain = sum(improvements) / len(improvements)
    
    # Scale to 0-100
    # -50% = 0, 0% = 50, +50% = 100
    score = 50 + (avg_gain * 1.0)
    return max(0, min(100, int(score)))

def _assess_risk(self, mutation: Dict) -> int:
    """How likely to break things? (0-100, high = risky)"""
    
    changes = mutation.get("proposed_changes", {})
    
    prompt = f"""
    Proposed changes: {changes}
    
    Risk assessment 0-100:
    0 = Zero risk, super safe
    100 = Dangerous, likely to fail
    
    Consider: Could this crash? Cause metrics to tank? 
    Lock us out? Break rollback?
    
    Return just the number.
    """
    
    risk = self._ask_agent_for_score(prompt)
    return max(0, min(100, risk))

def _rate_testability(self, mutation: Dict) -> int:
    """Can we safely evaluate it?"""
    
    changes = mutation.get("proposed_changes", {})
    
    # Check if we have good test coverage for these parameters
    # Check if rollback is straightforward
    
    prompt = f"""
    Changes: {changes}
    
    Can we safely test this?
    0 = Hard to test, risky to evaluate
    100 = Easy to test, safe evaluation
    
    Return just the number.
    """
    
    testability = self._ask_agent_for_score(prompt)
    return max(0, min(100, testability))

def _ask_agent_for_score(self, prompt: str) -> int:
    """Ask Alpha (evaluator) for a score."""
    response = self.agents["alpha_evaluator"].decide(prompt)
    try:
        return int(response.strip())
    except:
        return 50  # Default: neutral
```

**Update propose_mutation()**:

```python
def propose_mutation(self, agent_name, evaluation_result):
    # ... existing mission alignment code from Task 20 ...
    
    # NEW: Score the mutation
    quality_score = self.score_mutation(mutation_obj)
    
    # Only propose high-quality mutations
    if quality_score < 60:
        log(f"REJECTED: {mutation_id} - Low score: {quality_score}")
        return None
    
    log(f"PROPOSED: {mutation_id} - Score: {quality_score}, Pillar: {pillar}")
    return mutation_obj
```

**Acceptance Criteria**:
- Mutations have `quality_score` (0-100)
- Mutations have `quality_breakdown` (alignment, gain, risk, testability)
- Only mutations with score >= 60 are proposed
- Logs show rejected mutations with scores
- Quality score is reproducible (same mutation = same score)

**Test**:
```bash
# Check mutation files
grep "quality_score" evolution_mutations/*.json

# Verify all proposed mutations have score >= 60
grep "PROPOSED" logs/ | grep -v "Score: [6-9]" | grep -v "Score: 10"
```

---

## TASK 22: Create MUTATIONS_ROADMAP.md in GitHub

**What**: Public tracking of proposed mutations ranked by quality

**Where**: Create new file at repo root: `MUTATIONS_ROADMAP.md`

**Content template**:

```markdown
# Autonomous Mutation Roadmap

**Last Updated**: [timestamp from system]
**Total Proposed**: [count]
**Top Candidates**: [top 10 by score]

## 🎯 Next Mutations to Evaluate (Top 10)

| Rank | ID | Pillar | Description | Quality Score | Status |
|------|----|----|------------|--------------|--------|
| 1 | mut-0001 | Pillar 2 | Add Groq failover... | 92 | PROPOSED |
| 2 | mut-0002 | Pillar 1 | Optimize goal detection... | 87 | PROPOSED |
| ... |

## ✅ In Progress

| ID | Description | Approved | Started | Tests |
|----|-------------|----------|---------|-------|
| mut-0001 | Add Groq failover | ✅ | [date] | Running |

## ✅ Completed & Promoted

| ID | Description | Completed | Result | Metrics |
|----|-------------|-----------|--------|---------|
| mut-0000 | Optimize temperature... | [date] | ✅ Success | +5% accuracy |

## ❌ Rejected

| ID | Description | Reason | Score |
|----|-------------|--------|-------|
| mut-0999 | Disable voting... | Violates core governance | 12 |

---

## How This Works

1. Council proposes mutation
2. Kilo scores it (0-100)
3. If score >= 60, added to "Next Mutations"
4. Ranked by score
5. Operator approves → moves to "In Progress"
6. Evaluation completes → moves to "Completed" or rejected
7. File auto-updates with latest status
```

**Implementation**:

1. After each mutation proposed, append to MUTATIONS_ROADMAP.md:

```python
def update_roadmap(self, mutation_obj: Dict):
    """Update MUTATIONS_ROADMAP.md with new mutation."""
    
    roadmap_path = "MUTATIONS_ROADMAP.md"
    
    # Read current roadmap
    with open(roadmap_path, "r") as f:
        content = f.read()
    
    # Extract "Next Mutations" section
    # Add new mutation as row in table
    # Sort by quality score descending
    # Keep only top 10
    
    # Write back
    with open(roadmap_path, "w") as f:
        f.write(updated_content)
    
    # Commit to GitHub
    # git add MUTATIONS_ROADMAP.md
    # git commit -m f"Add mutation {mutation_obj['id']} (score: {mutation_obj['quality_score']})"
    # git push
```

2. Create automated update (run every 30 minutes):

```python
def roadmap_update_loop():
    while True:
        mutations = load_all_proposed_mutations()
        
        # Sort by quality score
        mutations.sort(key=lambda m: m["quality_score"], reverse=True)
        
        # Update MUTATIONS_ROADMAP.md
        update_roadmap(mutations[:10])
        
        # Commit if changed
        if git_status() != "clean":
            git_commit("Auto-update MUTATIONS_ROADMAP.md")
            git_push()
        
        time.sleep(1800)  # 30 minutes
```

**Acceptance Criteria**:
- MUTATIONS_ROADMAP.md exists in repo root
- Shows top 10 mutations by score
- Updates automatically after each mutation
- File is human-readable (Markdown table)
- Committed to GitHub (visible in repo)
- Operators can see which mutations are coming

**Test**:
```bash
# Check file exists
ls -la MUTATIONS_ROADMAP.md

# Check it's in git
git log MUTATIONS_ROADMAP.md

# Verify it has mutations
grep "mut-" MUTATIONS_ROADMAP.md | wc -l
```

---

## TASK 23: Document Mission Pillars in Agent Context

**What**: Inject mission pillar descriptions into agent prompts so they understand what they're optimizing for

**Where**: Create `core/agent_context.py`, update agent initialization

**New file: `core/agent_context.py`**:

```python
"""
Inject architecture awareness into agent prompts.
Agents must understand:
- Their role in the council
- The mission they serve
- What they can/can't do
"""

MISSION_PILLARS = {
    1: {
        "name": "Recursive Self-Evolution",
        "description": "Gap analysis → implement → validate → promote/rollback. Continuous self-improvement.",
        "how_to_help": "Propose mutations that make us better at learning from feedback"
    },
    2: {
        "name": "Autonomous Resource Optimization",
        "description": "Prefer free-tier inference. Cloud-first with failover. No single provider dependency.",
        "how_to_help": "Propose mutations that reduce costs or switch to cheaper providers"
    },
    3: {
        "name": "Model Agnosticism",
        "description": "Support 20+ cloud providers. Failover and load balancing. No hard dependencies.",
        "how_to_help": "Propose mutations that increase provider diversity or robustness"
    },
    4: {
        "name": "Durable Local State",
        "description": "Goals, configs, memory, audit logs persisted. SQLite + checkpoints. Recover from crashes.",
        "how_to_help": "Propose mutations that improve persistence or recovery speed"
    },
    5: {
        "name": "Companion Alignment",
        "description": "Telegram interface + human steering. Operator override. Transparent reporting.",
        "how_to_help": "Propose mutations that improve human-council communication or user control"
    }
}

COUNCIL_ARCHITECTURE = """
# Council Architecture

You are one of three agents in an autonomous council:
- **Autobot**: Orchestrator, security voter, operator interface
- **Alpha**: Mission alignment evaluator, voting member
- **Beta**: Feasibility evaluator, worker, voting member

## Decision Making
- All decisions require **unanimous consent** (all 3 must approve)
- No agent can override the voting requirement
- Deadlock → escalate to human operator

## What You Can Do
✅ Propose mutations aligned with mission
✅ Evaluate other agents' proposals critically
✅ Vote YES/NO on mutations
✅ Suggest improvements within your role
✅ Learn from execution feedback
✅ Report status and failures transparently

## What You CANNOT Do
❌ Override unanimous voting
❌ Modify core governance rules
❌ Access resources not provisioned
❌ Deploy to unapproved infrastructure
❌ Violate HMAC security requirements
❌ Make decisions without consulting other agents

## Your Mutation Proposals
When you propose a mutation, you MUST:
1. Declare which mission pillar it serves (1-5)
2. Explain the expected improvement
3. Estimate the risk
4. Suggest how to safely evaluate it
5. Provide a rollback plan
6. Be honest if unsure (don't guess)
"""

def get_agent_context_prompt(agent_name: str) -> str:
    """Get mission + architecture context for an agent."""
    
    return f"""
{COUNCIL_ARCHITECTURE}

---

## Mission Pillars (Why You Exist)

{chr(10).join(f'''
### Pillar {i}: {details["name"]}
**Description**: {details["description"]}
**How to Help**: {details["how_to_help"]}
'''
        for i, details in MISSION_PILLARS.items()
    )}

---

## Your Role: {agent_name}

[Role-specific instructions here]

Every mutation you propose must serve one of the 5 pillars.
If you can't identify which pillar, don't propose it.
"""

def inject_mission_context(agent_prompt: str) -> str:
    """Prepend mission context to any agent prompt."""
    context = get_agent_context_prompt("generic")
    return context + "\n\n" + agent_prompt
```

**Update agent initialization**:

```python
# In agents/autobot.py, agents/alpha_evaluator.py, agents/beta_worker.py

def __init__(self):
    self.mission_context = get_agent_context_prompt(self.name)
    # ... rest of init

def decide(self, task_prompt: str):
    # Inject mission context into every decision
    full_prompt = self.mission_context + "\n\n" + task_prompt
    return self.llm.call(full_prompt)
```

**Acceptance Criteria**:
- core/agent_context.py exists
- MISSION_PILLARS defined (all 5)
- COUNCIL_ARCHITECTURE explains governance
- Agents inject context before every decision
- Logs show agents referencing mission pillars

**Test**:
```bash
# Check imports work
python3 -c "from core.agent_context import get_agent_context_prompt; print(get_agent_context_prompt('autobot'))"

# Verify context is prepended to decisions
grep -A5 "COUNCIL_ARCHITECTURE" logs/agent_decisions.log
```

---

## SUMMARY: After Phase A

✅ **Mutations are MISSION-ALIGNED**
- Every mutation declares its pillar (1-5)
- Unaligned mutations are rejected

✅ **Mutations are QUALITY-SCORED**
- Score 0-100 (alignment, gain, risk, testability)
- Only score >= 60 are proposed
- Breakdown visible

✅ **MUTATIONS_ROADMAP.md public**
- Top 10 candidates visible in GitHub
- Auto-updates after each mutation
- Human operators can see what's coming

✅ **Agents understand their mission**
- Context injected into all decisions
- Know their pillars and constraints
- Understand governance rules

---

## HOW TO RUN PHASE A (For Martin's verification)

After Kilo commits:

```bash
# 1. Check mission alignment exists
grep -r "mission_pillar" evolution_mutations/ | head -1

# 2. Check quality scores exist
grep -r "quality_score" evolution_mutations/ | head -1

# 3. Check roadmap auto-updates
cat MUTATIONS_ROADMAP.md

# 4. Verify mutations are being filtered
grep "REJECTED.*Low score" logs/evolution.log
```

---

## Next Phase: Phase B (Self-Awareness)

After Phase A is working, Phase B will:
- Add self-deployment capability
- Plan for spider-web grid architecture
- Document what council knows about itself

Ready for Kilo to start?

