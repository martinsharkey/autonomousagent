# Gemini Feedback - Autonomy Gap Analysis

**Source:** Gemini peer review  
**Date:** 2026-07-28  
**Context:** Post-validation review of the autonomous mutation pipeline

## Summary Assessment

Gemini agrees with the diagnosis: the system has autonomous _process_ but not autonomous _outcome_. The feedback identifies three concrete gaps preventing promoted mutations from surviving and affecting behavior.

---

## Gap 1: Conquering the Pytest Gate (Primary Blocker)

**Problem:** 120s timeout causing every approved mutation to rollback.  
**Root causes to investigate:**
- Live API calls during pytest (LLM provider, Telegram)
- Integration tests mixed with unit tests
- Test suite too broad for automated gating

**Proposed fixes:**
1. Mock/stub external API calls during automated tests
2. Split suite into `test_fast.py` (logic) and `test_integration.py` (live)
3. Only gate promotion on fast tests; run integration tests async
4. Temporary band-aid: increase timeout to 300s to prove pipeline works

---

## Gap 2: Making Mutations Durable (Post-Merge Config Loading)

**Problem:** `merged_to_main: true` but agents don't load new config next cycle.  
**Root causes to investigate:**
- Daemon holds agent configs in memory across cycles
- No file watcher on `agent_configs/` directory
- Agents instantiated once, never re-read disk state

**Proposed fixes:**
1. Force daemon to read `agent_configs/.../active.json` from disk at start of each cycle
2. Implement `watchdog` file watcher on `agent_configs/` to trigger `reload_config()`
3. Ensure stateless cycles: every 60s boot afresh from disk state

---

## Gap 3: Patching the Governance Leak (`signature: null`)

**Problem:** Some rejected mutations have `signature: null` and `approval_timestamp: null`.  
**Root causes to investigate:**
- Validation pipeline bypassing council/governance on early failure
- Exceptions before governance stamping occurs
- No standardized rejection funnel

**Proposed fixes:**
1. Wrap entire proposal block in `try/except` and route failures to `system_reject()` that stamps `SYSTEM_REJECTED` signature
2. Use Pydantic dynamic defaults for `signature` and `approval_timestamp` to prevent `None` state
3. Ensure ALL mutations get stamped, regardless of success/failure path

---

## Key Question from Gemini

> To help narrow down that timeout issue: do you know if the test suite is currently attempting to spin up live agent interactions, or is it isolated entirely to local logic execution?

**Current status:** Unknown. Needs investigation.

## Investigation Findings (2026-07-28 17:00 UTC)

### Gap 1: Pytest Gate - ROOT CAUSE CONFIRMED

**Tests making live network calls:**
- `tests/test_providers_real.py` - Makes live HTTP calls via `httpx.AsyncClient` to Anthropic, OpenRouter, etc.
- `tests/test_new_providers.py` - Live HTTP calls via `httpx`
- `tests/test_original_providers.py` - Live HTTP calls via `httpx`

**Daemon test command:**
```python
# core/evolution.py line 696-702
result = subprocess.run(
    ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "-q"],
    capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT)
)
```

**Conclusion:** The 120s timeout is breached because the test suite includes integration tests that make real network calls to LLM providers. When those calls experience latency, rate limiting, or auth issues, the entire pytest run exceeds 120 seconds.

### Gap 2: Config Durability - MOSTLY WORKING

**Evidence:**
- `core/agent_config.py` line 64-76: `get_active()` reads `active.json` from disk on every call
- `agents/autobot.py` line 68: `autobot_node()` calls `_load_active_config("autobot")` on each invocation
- `agents/alpha_evaluator.py` line 31: Same pattern
- `agents/beta_worker.py` line 31: Same pattern
- `core/planning.py` line 33: `AgentPlanner.create_plan()` calls `get_active_with_defaults()` on each plan creation

**Singleton pattern:**
- `core/agent_config.py` line 234-239: `get_config_store()` returns a global singleton, but this is safe because `get_active()` reads from disk on each call.

**Verdict:** Config durability is **functionally working**. The singleton store isn't caching values; each agent node and planner reads fresh config from disk on every execution. If a mutation promotes a new config version and updates `active.json`, the next agent invocation will pick it up.

**Caveat:** If any component caches config values locally (not observed in current code), that would break durability. But based on the code paths traced, config is reloaded from disk.

### Gap 3: Governance Leak - CONFIRMED

**Evidence:**
- `core/evolution.py` line 304-317: Mission alignment rejection — `signature` NOT set, `approval_timestamp` remains `None`
- `core/evolution.py` line 328-342: Low quality score rejection — `signature` NOT set, `approval_timestamp` remains `None`
- `core/evolution.py` line 349-362: Quota exceeded rejection — `signature` NOT set, `approval_timestamp` remains `None`
- `core/evolution.py` line 364: `mutation.sign()` is ONLY called after all rejection checks pass

**Impact:** Any mutation that fails early validation (mission pillar, quality score, quota) bypasses governance stamping entirely. The mutation is saved with `signature: null` and `approval_timestamp: null`.

**What's missing:** A standardized `try/except` wrapper or a `system_reject()` function that stamps ALL rejections with `SYSTEM_REJECTED` signature and a timestamp.

---

## Quick Answer to Gemini's Key Question

> Do you know if the test suite is currently attempting to spin up live agent interactions, or is it isolated entirely to local logic execution?

**Answer:** The test suite includes **both**:
- **Local logic tests** (test_mutation_end_to_end.py, test_integration.py, test_code_validator.py, etc.)
- **Live network tests** (test_providers_real.py, test_new_providers.py, test_original_providers.py) that make real HTTP calls to LLM providers via `httpx`

The 120s timeout runs the **entire suite**, including live network tests. When those time out or experience latency, pytest fails and the mutation rolls back.

