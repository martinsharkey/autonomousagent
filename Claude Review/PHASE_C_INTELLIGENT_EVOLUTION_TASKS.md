# 🎯 PHASE C: INTELLIGENT AUTONOMOUS EVOLUTION

**Duration**: 4-6 hours  
**Owner**: Kilo Code  
**Objective**: Move from "temperature spam" to "meaningful autonomous evolution"  
**Success**: Agents evolve intelligently toward mission, not parameter tuning loops  

---

## PROBLEM STATEMENT

**Current state** (proven by evidence files):
- ✅ Mutation pipeline technically works
- ❌ Mutations are trivial (temperature adjustments)
- ❌ Same temperature proposed repeatedly
- ❌ Agents don't communicate
- ❌ No mission-driven reasoning
- ❌ Martin getting spammed with useless notifications

**Why**: System is restricted to config-only mutations + metric optimization + independent voting

**Solution**: 5 tasks to add intelligence

---

## TASK C1: Inter-Agent Communication Channel (90 min)

**Objective**: Agents can discuss mutations before voting, share reasoning

**Create**: core/agent_communication.py

**Structure**:
```python
class CouncilDiscussionSpace:
    """Shared space where agents reason together about mutations."""
    
    async def open_discussion(self, topic: str):
        """Open discussion on a topic (e.g., mutation proposal)"""
        discussion = {
            "id": generate_id(),
            "topic": topic,
            "participants": {},  # agent_name -> thoughts
            "consensus": None,
            "timestamp": now()
        }
        return discussion
    
    async def agent_contributes(self, discussion_id, agent_name, thoughts):
        """Agent adds their thinking to the discussion"""
        # Fetch discussion
        # Add agent's contribution
        # Detect consensus
        # Store
    
    async def get_discussion_summary(self, discussion_id):
        """Get what all agents have discussed"""
        # Return shared reasoning state
        # Use this when voting
```

**Usage in mutation proposal**:
```python
# OLD
mutation = proposer.propose(agent_name, performance)
votes = council.vote(mutation)  # Each votes independently

# NEW
discussion = discussion_space.open_discussion("Should we improve error handling?")

# Autobot shares analysis
await discussion_space.agent_contributes("autobot", 
    "I think we should focus on error recovery. Here's why...")

# Alpha evaluates
alpha_analysis = await alpha.analyze_mutation_for_mission(mutation)
await discussion_space.agent_contributes("alpha_evaluator", alpha_analysis)

# Beta assesses feasibility
beta_analysis = await beta.assess_feasibility(mutation)
await discussion_space.agent_contributes("beta_worker", beta_analysis)

# Vote with shared reasoning context
votes = council.vote(mutation, discussion_context=discussion)
```

**Tests**:
- Agent contributions stored correctly
- Discussion summary synthesizes all thoughts
- Voting uses discussion context
- Evidence: discussion_evidence.json with all three agents' reasoning

**Acceptance Criteria**:
- [ ] CouncilDiscussionSpace class functional
- [ ] Agents can contribute thoughts
- [ ] Discussion summary works
- [ ] Voting uses discussion context
- [ ] Test passes with evidence

---

## TASK C2: Mission-Aware Mutation Proposer (120 min)

**Objective**: Proposer generates mutations aligned to mission pillars, not just metric tuning

**Modify**: core/mutation_proposer.py

**Key changes**:

1. **Add mission context to proposer function**:
```python
async def propose_mutation(
    agent_name: str,
    performance: Dict[str, Any],
    recent_trajectories: Optional[List[str]],
    current_mission_pillar: int,  # NEW: Which pillar to focus on?
    council_discussion: Optional[str] = None,  # NEW: What did agents discuss?
) -> Dict[str, Any]:
```

2. **Update prompt to include mission**:
```python
PROMPT_TEMPLATE = """\
You are the Mutation Proposer for agent `{agent_name}`.

MISSION PILLARS:
- Pillar 1: Recursive Self-Evolution - improve ability to learn and adapt
- Pillar 2: Autonomous Resource Optimization - reduce costs and optimize free tier usage
- Pillar 3: Model Agnosticism - support multiple LLM providers
- Pillar 4: Durable Local State - improve persistence and recovery
- Pillar 5: Companion Alignment - improve human-council communication

CURRENT FOCUS PILLAR: Pillar {current_mission_pillar}

Your job: Propose mutations that ADVANCE Pillar {current_mission_pillar}

Recent performance: {performance_text}
Recent trajectories: {trajectory_text}
Council discussion: {council_discussion}

For Pillar {current_mission_pillar}, consider:
{pillar_specific_guidance}

Return JSON only with mutation proposal.
CRITICAL: Propose REAL improvements, not just parameter tweaking.
"""
```

3. **Add pillar-specific guidance**:
```python
PILLAR_GUIDANCE = {
    1: "Propose improvements to error handling, failure recovery, learning mechanisms, feedback loops",
    2: "Propose quota optimization, provider switching, request caching, batch processing",
    3: "Propose new provider support, improved failover, multi-provider testing",
    4: "Propose state management improvements, checkpoint verification, recovery procedures",
    5: "Propose Telegram improvements, natural language support, status reporting",
}
```

4. **Track pillar rotation**:
```python
async def select_mission_pillar():
    """Rotate through pillars cyclically"""
    current = load_current_pillar()
    next_pillar = (current % 5) + 1
    save_current_pillar(next_pillar)
    return next_pillar
```

**Tests**:
- Proposer generates pillar-specific suggestions
- Prompt includes current pillar guidance
- Output includes pillar ID
- Evidence: step2_proposer_evidence.json shows pillar 1, 2, etc mutations

**Acceptance Criteria**:
- [ ] Proposer takes mission_pillar parameter
- [ ] Prompt includes pillar-specific guidance
- [ ] Output references pillar in mutation
- [ ] Pillar rotation works
- [ ] Test passes with evidence showing Pillar-specific mutations

---

## TASK C3: Mutation Deduplication (60 min)

**Objective**: Prevent temperature spam by detecting repeated mutation proposals

**Create**: core/mutation_deduplicator.py

```python
class MutationDeduplicator:
    """Prevent proposing same mutation repeatedly (loop detection)."""
    
    def __init__(self, history_dir="evolution/mutations", window_hours=24):
        self.history_dir = history_dir
        self.window_hours = window_hours
        self.proposed_cache = {}
    
    def _mutation_fingerprint(self, mutation: Dict) -> str:
        """Create fingerprint of mutation (ignores ID, timestamp)"""
        key = (
            mutation.get("agent_name"),
            mutation.get("mutation_type"),
            json.dumps(mutation.get("proposed_changes"), sort_keys=True)
        )
        return hashlib.sha256(str(key).encode()).hexdigest()
    
    async def should_propose(self, mutation: Dict) -> bool:
        """Check if this mutation should be proposed"""
        fingerprint = self._mutation_fingerprint(mutation)
        
        # Check if proposed recently
        similar = await self._find_similar_recent(fingerprint)
        
        if similar:
            # Found recent similar mutation
            last_proposed = similar[-1]["timestamp"]
            days_ago = (now() - last_proposed).days
            
            if days_ago < 1:  # Within 24 hours
                # Don't propose again
                return False
        
        # Novel mutation, OK to propose
        return True
    
    async def _find_similar_recent(self, fingerprint: str) -> List[Dict]:
        """Find similar mutations proposed recently"""
        cutoff = now() - timedelta(hours=self.window_hours)
        similar = []
        
        for mutation_file in sorted(glob(f"{self.history_dir}/*.json"), reverse=True):
            with open(mutation_file) as f:
                mut = json.load(f)
            
            if mut.get("timestamp") < cutoff:
                break  # Too old, stop searching
            
            if self._mutation_fingerprint(mut) == fingerprint:
                similar.append(mut)
        
        return similar
    
    async def record_proposed(self, mutation: Dict):
        """Record that this mutation was proposed"""
        # Just saving it normally already records it
        pass
```

**Usage in proposer**:
```python
async def propose_mutation(...) -> Dict:
    mutation = generate_mutation(...)
    
    # NEW: Check for duplicates
    deduplicator = MutationDeduplicator()
    if not await deduplicator.should_propose(mutation):
        # Skip this one, it was proposed recently
        return None
    
    return mutation
```

**Tests**:
- Fingerprint identical mutations
- Detect mutation proposed 2 hours ago (should skip)
- Allow mutation proposed 25 hours ago (new proposal OK)
- Evidence: dedup_evidence.json showing skipped duplicates

**Acceptance Criteria**:
- [ ] MutationDeduplicator class works
- [ ] Fingerprinting works (same mutation = same fingerprint)
- [ ] Recent detection works (24-hour window)
- [ ] Dedup gate prevents proposals
- [ ] Test passes with evidence

---

## TASK C4: Switch to LiteLLM for Provider Management (120 min)

**Objective**: Replace custom router with battle-tested LiteLLM library

**Why**: 
- ✅ Handles 20+ providers seamlessly
- ✅ Built-in retry logic
- ✅ Better error handling
- ✅ Less code to maintain
- ✅ Industry standard

**Steps**:

1. **Install LiteLLM**:
```bash
pip install litellm
```

2. **Create core/llm_provider.py** (replaces parts of api_router.py):
```python
import litellm
from typing import Dict, List, Optional

class LLMProvider:
    """Simple wrapper around LiteLLM for consistent API."""
    
    def __init__(self):
        # LiteLLM reads from environment variables automatically
        # LITELLM_OPENROUTER_API_KEY=...
        # LITELLM_GROQ_API_KEY=...
        # etc.
        pass
    
    async def call(
        self,
        messages: List[Dict],
        model: str = "openrouter/claude-3.5-sonnet",
        fallback_models: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict:
        """Call LLM with automatic failover."""
        
        try:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=30
            )
            return response
        
        except litellm.RateLimitError:
            # Try fallback models
            if fallback_models:
                for fallback in fallback_models:
                    try:
                        response = await litellm.acompletion(
                            model=fallback,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                        return response
                    except Exception:
                        continue
            raise
        
        except Exception as e:
            raise Exception(f"LLM call failed: {e}")
    
    async def call_with_routing(
        self,
        messages: List[Dict],
        model_preference: str = "openrouter",
        temperature: float = 0.7
    ) -> Dict:
        """Route to best available model."""
        
        models_to_try = [
            f"{model_preference}/claude-3.5-sonnet",
            "groq/llama-3.1-8b",
            "deepseek-chat",
            "openai/gpt-4-turbo"  # If OPENAI key available
        ]
        
        response = await self.call(
            messages=messages,
            model=models_to_try[0],
            fallback_models=models_to_try[1:],
            temperature=temperature
        )
        
        return response
```

3. **Update proposer to use LiteLLM**:
```python
# OLD
from core.api_router import get_llm_router
router = get_llm_router()
response = await router.route_request(messages=..., temperature=...)

# NEW
from core.llm_provider import LLMProvider
provider = LLMProvider()
response = await provider.call_with_routing(messages=..., temperature=...)
```

4. **Configure environment** (.env):
```
LITELLM_OPENROUTER_API_KEY=your_key
LITELLM_GROQ_API_KEY=your_key
LITELLM_DEEPSEEK_API_KEY=your_key
# LiteLLM handles the rest automatically
```

5. **Remove custom provider management code**:
- Delete or repurpose parts of core/api_router.py that duplicate LiteLLM
- Keep only integration layer

**Tests**:
- LLMProvider can call OpenRouter Claude
- Fallback works (switch to Groq if OpenRouter rate limited)
- All agent models use LLMProvider
- Evidence: provider_evidence.json showing successful calls

**Acceptance Criteria**:
- [ ] LiteLLM installed and configured
- [ ] LLMProvider class works
- [ ] All agents use LLMProvider
- [ ] Fallover works (tested by mocking rate limit)
- [ ] Tests pass, no regression in functionality

---

## TASK C5: Expand VALID_PARAMS to Real Code Changes (90 min)

**Objective**: Allow proposer to suggest real code improvements (not just config)

**Currently**: VALID_PARAMS restricts to temperature, max_retries, system_prompt

**Needed**: Allow file_changes (with validation)

**Modify**: core/evolution.py

```python
# Current (config only)
VALID_PARAMS = {
    "autobot": ["temperature", "max_retries", "system_prompt"],
    "alpha_evaluator": ["temperature", "system_prompt"],
    "beta_worker": ["temperature", "system_prompt"],
}

# NEW: Include file changes
ALLOWED_FILE_PATHS = {
    "agents/": {
        "allowed": True,
        "description": "Agent implementation improvements"
    },
    "core/evolution.py": {
        "allowed": True,
        "description": "Evolution engine improvements"
    },
    "core/agent_communication.py": {
        "allowed": True,
        "description": "Communication channel"
    }
}

DENIED_FILE_PATHS = [
    ".env", "secrets/", ".gitignore", "*.key", "*.pem"
]

def validate_file_change(file_path: str) -> bool:
    """Check if file change is allowed"""
    
    # Check denied list first
    for denied in DENIED_FILE_PATHS:
        if fnmatch.fnmatch(file_path, denied):
            return False
    
    # Check allowed list
    for allowed in ALLOWED_FILE_PATHS:
        if fnmatch.fnmatch(file_path, allowed):
            return True
    
    return False  # Default deny
```

**Update propose_mutation validation**:
```python
def propose_mutation(...):
    # Existing code validation
    if "proposed_changes" in proposed_mutation:
        if "file_changes" in proposed_mutation["proposed_changes"]:
            # NEW: Validate file paths
            for file_path in proposed_mutation["proposed_changes"]["file_changes"]:
                if not validate_file_change(file_path):
                    raise ValueError(f"File change not allowed: {file_path}")
```

**Update mutation proposer prompt**:
```python
# Add to proposer prompt:
PROMPT_TEMPLATE = """\
...
ALLOWED CHANGES:
- Config parameters: temperature, system_prompt, max_retries
- File changes: agents/*, core/evolution.py, core/agent_communication.py
  (but NOT .env, secrets/, or other sensitive files)

You can propose either config changes OR file changes (or both).
For file changes, provide:
- file_path
- change_description
- code changes or pseudocode
...
"""
```

**Tests**:
- File change validation works
- Denied paths rejected (e.g., .env)
- Allowed paths accepted (e.g., agents/autobot.py)
- Proposer generates file change mutations
- Evidence: code_mutation_evidence.json showing real code changes

**Acceptance Criteria**:
- [ ] File validation logic works
- [ ] Denied paths properly rejected
- [ ] Allowed paths properly allowed
- [ ] Proposer generates file change mutations
- [ ] Tests pass with evidence

---

## IMPLEMENTATION ORDER

1. **First** (Task C1): Add inter-agent communication
   - Enables agents to discuss mutations
   - Foundation for smarter voting

2. **Second** (Task C2): Make proposer mission-aware
   - Proposer generates pillar-aligned mutations
   - Rotates through pillars

3. **Third** (Task C3): Add deduplication
   - Prevents temperature spam
   - No more repeated proposals

4. **Fourth** (Task C4): Switch to LiteLLM
   - Better provider management
   - Simpler, more robust code

5. **Fifth** (Task C5): Expand allowed mutations
   - Proposer can suggest real code changes
   - True autonomous evolution

---

## SUCCESS CRITERIA (Phase C Complete)

After all 5 tasks:

✅ **Agents communicate together**
- Discussion space works
- Shared reasoning before voting

✅ **Mutations are mission-aligned**
- Focused on Pillar 1, 2, 3, 4, 5 in rotation
- Not just metric optimization

✅ **No temperature spam**
- Deduplication prevents loops
- Each mutation is novel

✅ **Better LLM management**
- Using LiteLLM (industry standard)
- Cleaner code

✅ **Real evolution possible**
- File changes allowed and tested
- Can propose actual code improvements

✅ **Evidence collected**
- Timestamps for all 5 tasks
- Test results showing improvements
- Telegram shows meaningful mutations (not spam)

---

## EXPECTED OUTCOME (After Phase C)

**Before Phase C**:
- "Adjust temperature to 0.2" (spam)
- "Adjust temperature to 0.15" (spam)
- "Max retries to 4" (trivial)

**After Phase C**:
- "Improve error handling (Pillar 1) - add retry logic with backoff"
- "Optimize quota usage (Pillar 2) - implement response caching"
- "Add Groq provider (Pillar 3) - improved failover"
- "Better persistence (Pillar 4) - snapshot verification"
- "Natural language Telegram (Pillar 5) - intent parser"

**Agents discuss**: "Should we focus on error handling or quota optimization?"

**Result**: **Meaningful autonomous evolution toward mission**

---

## TIMELINE

| Task | Time | Cumulative |
|------|------|-----------|
| C1: Inter-agent comm | 90 min | 90 min |
| C2: Mission-aware | 120 min | 210 min |
| C3: Deduplication | 60 min | 270 min |
| C4: LiteLLM | 120 min | 390 min |
| C5: File changes | 90 min | 480 min |
| **TOTAL** | | **8 hours** |

---

## WHAT TO DO NOW

Send this to Kilo with:

> "Phase C is the intelligence layer. It takes the mutation pipeline (which works perfectly) and makes it actually SMART.
>
> 5 tasks, 8 hours total. Do them in order.
>
> After C5: Agents will be meaningfully autonomous, not spamming temperature adjustments.
>
> Ready?"

