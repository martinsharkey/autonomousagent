# 🔧 KILO'S PHASE A FIX TASKS

**Status**: Phase A partially complete, critical fixes needed before proceeding  
**Owner**: Kilo Code  
**Duration**: 2-3 hours  
**Priority**: CRITICAL - System generating mutations but can't validate quality or manage resources

---

## THE PROBLEM STATEMENT

Martin sees 637 mutations but has **no visibility** into:
- Are they actually good quality?
- Are they aligned with the mission?
- Will they exhaust free tier quotas?

Current system generates mutations but **bypasses validation**. This is risky because:
- ❌ Bad mutations could waste resources
- ❌ Invalid parameters could cause evaluation failures
- ❌ No tracking of API costs per mutation
- ❌ Could burn through free tiers in hours

---

## TASK 24: Diagnose Mutation Creation Code Paths

**Objective**: Find where mutations are actually being created and why they bypass quality validation

**What to do**:

```bash
# 1. Find ALL places where Mutation objects are created
grep -r "Mutation(" core/ agents/ evolution/ --include="*.py" | tee mutation_creation_sites.txt

# 2. Find all places score_mutation() is called
grep -r "score_mutation(" --include="*.py"

# 3. Check if quality_score is being saved to mutations
grep -rn "quality_score" evolution/ --include="*.py"

# 4. Find where invalid params (learning_rate, exploration_factor) come from
grep -rn "learning_rate\|exploration_factor" --include="*.py"
```

**Report back**:
- [ ] Which code paths create mutations?
- [ ] Which ones call score_mutation()?
- [ ] Which ones save quality_score?
- [ ] Where do invalid params originate?

**Expected findings**:
- Likely: Mutations created in multiple places, not all going through validation
- Likely: Some path skipping quality scoring
- Likely: Mutation JSON not including score when saved

---

## TASK 25: Wire All Mutations Through Quality Validation

**Objective**: Ensure EVERY mutation is quality-scored, mission-aligned, validated

**Where**: `core/evolution.py`, function `propose_mutation()`

**Current code** (incomplete):
```python
def propose_mutation(self, agent_name, evaluation_result):
    # ... build proposed_changes ...
    
    VALID_PARAMS = {
        "autobot": ["temperature", "max_retries", "system_prompt"],
        "alpha_evaluator": ["temperature", "system_prompt"],
        "beta_worker": ["temperature", "system_prompt"],
    }
    
    # Validate parameters
    valid_keys = VALID_PARAMS.get(agent_name, [])
    for key in proposed_changes.keys():
        if key not in valid_keys:
            raise ValueError(...)
    
    # ... but then what? Score it? Set mission pillar?
```

**What's missing**: After VALID_PARAMS check, need:
1. Set mission_pillar
2. Call score_mutation()
3. Check score >= 60
4. Estimate resource impact
5. Save mutation with ALL fields

**New implementation**:

```python
def propose_mutation(self, agent_name, evaluation_result):
    """Propose a mutation with full validation and scoring."""
    
    # Build proposed changes (existing logic)
    proposed_changes = self._build_proposed_changes(agent_name, evaluation_result)
    
    # ===== STEP 1: VALIDATE PARAMETERS =====
    VALID_PARAMS = {
        "autobot": ["temperature", "max_retries", "system_prompt"],
        "alpha_evaluator": ["temperature", "system_prompt"],
        "beta_worker": ["temperature", "system_prompt"],
    }
    
    valid_keys = VALID_PARAMS.get(agent_name, [])
    for key in proposed_changes.keys():
        if key not in valid_keys:
            log(f"REJECTED: Invalid parameter '{key}' for {agent_name}")
            return None  # REJECT
    
    # ===== STEP 2: CLASSIFY MISSION PILLAR =====
    mission_pillar = self._classify_mutation_pillar(agent_name, proposed_changes)
    if mission_pillar is None:
        log(f"REJECTED: No mission alignment identified")
        return None  # REJECT
    
    # ===== STEP 3: SCORE MUTATION =====
    mutation_obj = {
        "mutation_id": str(uuid.uuid4()),
        "agent_name": agent_name,
        "proposed_changes": proposed_changes,
        "mission_pillar": mission_pillar,
        "status": "proposed",
        "timestamp": datetime.now().isoformat(),
    }
    
    quality_score = self.score_mutation(mutation_obj)
    mutation_obj["quality_score"] = quality_score
    
    if quality_score < 60:
        log(f"REJECTED: Score too low ({quality_score})")
        return None  # REJECT
    
    # ===== STEP 4: ESTIMATE RESOURCE IMPACT =====
    resource_impact = self._estimate_resource_impact(proposed_changes)
    mutation_obj["resource_impact"] = resource_impact
    
    # ===== STEP 5: SAVE MUTATION =====
    mutation_path = f"evolution/mutations/mutation_{mutation_obj['mutation_id']}.json"
    with open(mutation_path, "w") as f:
        json.dump(mutation_obj, f, indent=2)
    
    log(f"PROPOSED: {mutation_obj['mutation_id']} - Score: {quality_score}, Pillar: {mission_pillar}, Resource: {resource_impact}")
    return mutation_obj
```

**Acceptance Criteria**:
- [ ] VALID_PARAMS validation runs and rejects invalid params
- [ ] Mission pillar is set (1-5)
- [ ] Quality score is calculated and saved
- [ ] Resource impact is estimated and saved
- [ ] Only mutations with score >= 60 are proposed
- [ ] Logs show rejected mutations with reason
- [ ] NO mutations without quality_score, mission_pillar, resource_impact

**Test**:
```bash
# After running, verify a mutation has all required fields
cat evolution/mutations/mutation_*.json | python3 -c "
import json, sys
m = json.load(sys.stdin)
assert 'quality_score' in m
assert 'mission_pillar' in m
assert 'resource_impact' in m
assert m['quality_score'] >= 60
print('✅ PASSED')
"
```

---

## TASK 26: Fix VALID_PARAMS Validation

**Objective**: Ensure invalid parameters are caught and rejected

**Current code**: Appears to have validation but mutations have invalid params anyway

**Problem**:
- Found mutations with "learning_rate", "exploration_factor"
- These should be rejected by VALID_PARAMS check
- Either check not running, or being bypassed

**Check these files**:
1. `core/evolution.py` - Is VALID_PARAMS check actually running?
2. `agents/*/evolution.py` - Any agent-specific mutation paths bypassing validation?
3. `evolution/engine.py` - Does main evolution loop call validation?
4. `autonomous_loops/` - Any direct mutation creation?

**What needs to be true**:
```python
# ONLY these are valid - nothing else:
VALID_PARAMS = {
    "autobot": ["temperature", "max_retries", "system_prompt"],
    "alpha_evaluator": ["temperature", "system_prompt"],
    "beta_worker": ["temperature", "system_prompt"],
}

# If you see in mutations:
# - learning_rate → PROBLEM, should be rejected
# - exploration_factor → PROBLEM, should be rejected
# - strategy → PROBLEM, should be rejected
# - success_rate → PROBLEM, should be rejected
```

**Action**:
1. Find all places that create mutations
2. Ensure ALL go through VALID_PARAMS validation
3. If any bypass it, wire them through validation
4. Remove or comment out any direct mutation creation

**Acceptance Criteria**:
- [ ] NO mutations with invalid parameters
- [ ] All future mutations only use: temperature, max_retries (autobot only), system_prompt
- [ ] VALID_PARAMS check is enforced everywhere

**Test**:
```bash
# Check NO invalid params in any mutation
grep -l "learning_rate\|exploration_factor\|strategy\|success_rate" \
  evolution/mutations/*.json && echo "❌ FAILED: Found invalid params" || echo "✅ PASSED"
```

---

## TASK 27: Add Resource Impact Estimation

**Objective**: Track API cost/quota usage for each mutation type

**Where**: `core/evolution.py`, new function `_estimate_resource_impact()`

**What it should do**:
```python
def _estimate_resource_impact(self, proposed_changes: Dict) -> Dict:
    """Estimate API calls and quota impact of a mutation."""
    
    impact = {
        "api_calls_estimate": 0,
        "providers_affected": [],
        "quota_impact_percent": 0.0,
        "risk_level": "low"  # low, medium, high
    }
    
    # Example: temperature change = minimal cost
    if "temperature" in proposed_changes:
        impact["api_calls_estimate"] += 5  # Few calls to test
        impact["providers_affected"] = ["openrouter", "groq", "deepseek"]
    
    # Example: system_prompt change = medium cost
    if "system_prompt" in proposed_changes:
        impact["api_calls_estimate"] += 20  # More calls needed to evaluate
        impact["risk_level"] = "medium"
    
    # Calculate quota impact (assume 1000 calls per day free)
    DAILY_QUOTA = 1000
    CURRENT_USAGE = self.get_current_api_usage()  # Query provider status
    AVAILABLE = DAILY_QUOTA - CURRENT_USAGE
    
    if impact["api_calls_estimate"] > AVAILABLE * 0.8:
        impact["risk_level"] = "high"
        impact["quota_impact_percent"] = (impact["api_calls_estimate"] / AVAILABLE) * 100
    
    return impact
```

**Key fields needed**:
- `api_calls_estimate`: How many API calls will this mutation need?
- `providers_affected`: Which providers will be used?
- `quota_impact_percent`: % of daily quota this will use
- `risk_level`: low/medium/high based on quota available

**Acceptance Criteria**:
- [ ] Every mutation has resource_impact in JSON
- [ ] api_calls_estimate is realistic
- [ ] Mutations flagged as "high" risk if would exceed 80% quota
- [ ] MUTATIONS_ROADMAP.md shows resource impact

**Test**:
```bash
# Check mutations have resource impact
grep "resource_impact" evolution/mutations/*.json | wc -l
# Should equal total mutation count

# Check high-risk mutations are tracked
grep "high" evolution/mutations/*.json | grep "risk_level"
```

---

## TASK 28: Track Provider Quota Usage

**Objective**: Implement quota monitoring per provider

**New file**: `core/quota_monitor.py`

```python
"""Track free-tier quota usage per provider."""

import json
from datetime import datetime, timedelta

class QuotaMonitor:
    def __init__(self):
        self.quota_state = "quota_state.json"
        self.load_state()
    
    def load_state(self):
        """Load current quota tracking."""
        try:
            with open(self.quota_state, "r") as f:
                self.state = json.load(f)
        except:
            self.state = {
                "openrouter": {"daily_limit": 1000, "used_today": 0},
                "groq": {"daily_limit": 1000, "used_today": 0},
                "deepseek": {"daily_limit": 1000, "used_today": 0},
                "last_reset": datetime.now().isoformat(),
            }
            self.save_state()
    
    def track_api_call(self, provider: str, calls: int = 1):
        """Record API call usage."""
        if provider in self.state:
            self.state[provider]["used_today"] += calls
            self.save_state()
    
    def get_available_quota(self, provider: str) -> int:
        """Get remaining quota for provider."""
        if provider not in self.state:
            return 0
        limit = self.state[provider]["daily_limit"]
        used = self.state[provider]["used_today"]
        return max(0, limit - used)
    
    def can_afford_mutation(self, provider: str, estimated_calls: int) -> bool:
        """Can we afford this mutation?"""
        available = self.get_available_quota(provider)
        # Only proceed if >20% quota buffer remains
        return estimated_calls <= (available * 0.8)
    
    def get_status(self) -> Dict:
        """Get quota status report."""
        status = {}
        for provider, data in self.state.items():
            if provider != "last_reset":
                used = data["used_today"]
                limit = data["daily_limit"]
                percent = (used / limit) * 100 if limit > 0 else 0
                status[provider] = {
                    "used": used,
                    "limit": limit,
                    "percent": percent,
                    "available": limit - used
                }
        return status
    
    def reset_daily(self):
        """Reset quota counters at midnight."""
        for provider in self.state:
            if provider != "last_reset":
                self.state[provider]["used_today"] = 0
        self.state["last_reset"] = datetime.now().isoformat()
        self.save_state()
    
    def save_state(self):
        """Persist quota state to file."""
        with open(self.quota_state, "w") as f:
            json.dump(self.state, f, indent=2)
```

**Wire into propose_mutation()**:
```python
def propose_mutation(self, agent_name, evaluation_result):
    # ... existing validation ...
    
    # Check if we can afford this mutation
    resource_impact = self._estimate_resource_impact(proposed_changes)
    
    # Get primary provider (usually openrouter)
    primary_provider = "openrouter"  # Or determine from config
    
    if not self.quota_monitor.can_afford_mutation(primary_provider, resource_impact["api_calls_estimate"]):
        log(f"REJECTED: Would exceed quota on {primary_provider}")
        return None  # Don't propose expensive mutations if quota tight
    
    # ... rest of mutation proposal ...
```

**Acceptance Criteria**:
- [ ] quota_monitor.py exists and tracks per-provider usage
- [ ] Mutations rejected if would exceed safe quota levels
- [ ] Status available for Telegram reporting
- [ ] Daily reset happens at midnight
- [ ] Logs show quota rejections

---

## TASK 29: Update MUTATIONS_ROADMAP.md to Show Resource Impact

**Objective**: Make resource impact visible in roadmap

**Update MUTATIONS_ROADMAP.md**:

```markdown
# Autonomous Mutation Roadmap

**Last Updated**: [auto]
**Status**: Phase A - Mission-Aligned + Resource-Aware Mutations

## Quality Legend
- 🟢 Green (Score 80-100): Excellent
- 🟡 Yellow (Score 60-79): Good
- 🔴 Red (Score < 60): Not proposed

## Resource Impact Legend
- 💚 Low (<5 API calls)
- 🟡 Medium (5-50 calls)
- 🔴 High (50+ calls)

## Top Mutations (Next 10)

| Rank | ID | Pillar | Description | Score | Resource | Status |
|------|----|----|----------|-------|----------|--------|
| 1 | mut-001 | 2 | Add Groq failover | 92 | 💚 Low | PROPOSED |
| 2 | mut-002 | 1 | Optimize goal detection | 87 | 🟡 Med | PROPOSED |
| ... |

## Quota Status

**OpenRouter**: 450/1000 calls today (45%) - 550 remaining  
**Groq**: 200/1000 calls today (20%) - 800 remaining  
**DeepSeek**: 100/1000 calls today (10%) - 900 remaining  

High-cost mutations paused on OpenRouter (>80% quota).

## Rejected (Quota Exhausted or Low Score)

| ID | Reason | Score | Est. Cost |
|----|--------|-------|-----------|
| mut-999 | Would exceed OpenRouter quota | 45 | 200 calls |
```

**Acceptance Criteria**:
- [ ] MUTATIONS_ROADMAP shows quality scores (not N/A)
- [ ] Shows resource impact (Low/Med/High)
- [ ] Shows quota status per provider
- [ ] Shows why mutations were rejected
- [ ] Updates automatically

---

## SUMMARY OF FIXES

| Task | What | Why | Duration |
|------|------|-----|----------|
| 24 | Diagnose mutation paths | Find where validation is bypassed | 20 min |
| 25 | Wire validation pipeline | Ensure ALL mutations go through checks | 45 min |
| 26 | Fix VALID_PARAMS | Block invalid parameters | 20 min |
| 27 | Add resource tracking | Know API cost of each mutation | 30 min |
| 28 | Implement quota monitor | Track usage, prevent burnout | 30 min |
| 29 | Update roadmap | Show quality + resources | 15 min |

**Total**: 2.5 hours

---

## BEFORE YOU START

1. Read: `MARTINS_ACTUAL_MISSION_REFRAMED.md` - Understand the context
2. Read: `PHASE_A_CRITICAL_ANALYSIS_AND_DIAGNOSIS.md` - Understand the problems
3. Verify git is clean: `git status`
4. Create feature branch: `git checkout -b phase-a-fixes`

---

## AFTER YOU FINISH

1. Run tests:
```bash
# Check no invalid params
grep -l "learning_rate\|exploration_factor" evolution/mutations/*.json && echo "FAIL" || echo "PASS"

# Check all mutations have required fields
for f in evolution/mutations/*.json; do
  python3 -c "
  import json
  m = json.load(open('$f'))
  assert 'quality_score' in m, f'Missing quality_score'
  assert 'mission_pillar' in m, f'Missing mission_pillar'
  assert 'resource_impact' in m, f'Missing resource_impact'
  assert m['quality_score'] >= 60, f'Score too low'
  " && echo "✅ $f" || echo "❌ $f"
done
```

2. Commit and push:
```bash
git add -A
git commit -m "Phase A Fixes: Resource tracking + quality validation enforcement"
git push origin phase-a-fixes
```

3. Report:
```
Completed Tasks 24-29 (Phase A fixes)

✅ Mutation validation pipeline wired
✅ VALID_PARAMS validation enforced
✅ Quality scores saved for all mutations
✅ Resource impact estimated and tracked
✅ Quota monitoring implemented
✅ MUTATIONS_ROADMAP.md updated with resources

All mutations now have:
- quality_score (>= 60 only)
- mission_pillar (1-5)
- resource_impact (API calls + provider)

System ready for Phase B: Self-Deployment
```

---

## Questions Before Starting?

Ask Martin if anything unclear. This is critical path work.

