# Rollback Plan - Gemini Fixes (2026-07-28)

## Fixes Implemented

1. **Fix #1 (Pytest Gate):**
   - Added `pytestmark = pytest.mark.live` to `tests/test_providers_real.py`, `tests/test_new_providers.py`, `tests/test_original_providers.py`
   - Updated `core/evolution.py::_run_tests_after_mutation()` to run targeted test subset instead of full `tests/` directory:
     - `tests/test_mutation_end_to_end.py`
     - `tests/test_integration.py`
     - `tests/test_council_unanimous_voting.py`
     - `tests/test_control_plane_e2e.py`
   - Added `-m "not live"` marker exclusion

2. **Fix #2 (Config Durability):**
   - No code changes required
   - Verified agents reload config from disk via `get_active()` / `_load_active_config()`

3. **Fix #3 (Governance Leak):**
   - Added `Mutation.system_reject(reason)` method in `core/evolution.py`
   - Replaced raw state updates with `system_reject()` in 3 early rejection paths:
     - Mission alignment rejection
     - Low quality score rejection
     - Quota exceeded rejection

## Rollback Procedure

If fixes cause regressions, roll back in this order:

### Step 1: Revert `core/evolution.py`
```bash
git checkout HEAD -- core/evolution.py
```
This reverts:
- `system_reject()` method
- All 3 rejection path changes
- `_run_tests_after_mutation()` targeted subset change

### Step 2: Revert test files
```bash
git checkout HEAD -- tests/test_providers_real.py tests/test_new_providers.py tests/test_original_providers.py
```

### Step 3: Verify clean state
```bash
git status
git diff --stat
```

### Step 4: Re-run verification
```bash
python -m pytest tests/test_mutation_end_to_end.py -v
```

## Known Risks

1. **Targeted test subset may miss failures:** Running only 4 test files instead of full suite means some regressions won't be caught. Mitigation: full suite still runs manually/integration environments.

2. **`system_reject()` changes mutation audit trail:** Previously rejected mutations had `signature: null`. Now they have `signature: "SYSTEM_REJECTED"`. This is a schema change that may affect downstream consumers.

3. **Live tests excluded from automation:** `test_providers_real.py`, `test_new_providers.py`, `test_original_providers.py` no longer run in automated pipeline. These must be run manually when needed.

## Rollback Triggers

Roll back if:
- Mutations still rollback after 120s with targeted tests
- `system_reject()` causes new errors in mutation storage
- Targeted tests miss a real failure that full suite would catch
- Session log shows new exceptions after fix deployment
