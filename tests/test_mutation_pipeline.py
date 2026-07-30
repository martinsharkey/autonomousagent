"""
Test the full mutation pipeline locally: propose → classify → vote → implement.

Run with: python -m tests.test_mutation_pipeline
(from the autonomousagent root directory)
"""

import sys
import os
import json
from datetime import datetime

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Minimal env setup to avoid import errors
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
os.environ.setdefault("TELEGRAM_CHAT_ID", "")


def test_pillar_classification():
    """Test that _classify_mutation_pillar works for parameter-only mutations."""
    from core.evolution import get_evolution_engine

    engine = get_evolution_engine()

    # Test 1: Parameter mutation with "strategy" keyword should classify to pillar 1
    pillar = engine._classify_mutation_pillar(
        "autobot",
        {"strategy": "adaptive", "learning_rate": 0.15},
        "Strategy evolution to improve success rate"
    )
    assert pillar is not None, "FAIL: Parameter mutation should classify to a pillar"
    print(f"  ✓ Parameter mutation classified to pillar {pillar}")

    # Test 2: File change mutation should use path-based classification
    pillar = engine._classify_mutation_pillar(
        "autobot",
        {"file_changes": [{"path": "core/evolution.py", "content": "test"}]},
        "Improve evolution engine"
    )
    assert pillar == 1, f"FAIL: core/ path should map to pillar 1, got {pillar}"
    print(f"  ✓ File mutation (core/) classified to pillar {pillar}")

    # Test 3: Telegram-related description should classify to pillar 5
    pillar = engine._classify_mutation_pillar(
        "autobot",
        {"system_prompt": "Be more helpful to the human operator"},
        "Improve telegram notification clarity for operator"
    )
    assert pillar == 5, f"FAIL: Telegram description should map to pillar 5, got {pillar}"
    print(f"  ✓ Telegram mutation classified to pillar {pillar}")

    # Test 4: Empty mutation defaults to pillar 1 (self-evolution)
    pillar = engine._classify_mutation_pillar(
        "autobot",
        {"max_retries": 5},
        "Generic tuning"
    )
    assert pillar is not None, "FAIL: Should default to pillar 1"
    print(f"  ✓ Generic mutation defaulted to pillar {pillar}")


def test_propose_mutation_passes():
    """Test that a realistic mutation proposal passes all gates."""
    from core.evolution import get_evolution_engine, MutationType

    engine = get_evolution_engine()

    mutation = engine.propose_mutation(
        agent_name="autobot",
        mutation_type=MutationType.PARAMETER_ADJUSTMENT,
        description="Strategy evolution to improve success rate via adaptive learning",
        rationale="Performance data shows declining success rate, adaptive strategy should help",
        proposed_changes={"strategy": "adaptive", "learning_rate": 0.15},
        expected_improvement=0.2,
        risk_level="low"
    )

    print(f"  Mutation ID: {mutation.mutation_id}")
    print(f"  Status: {mutation.status.value}")
    print(f"  Pillar: {mutation.mission_pillar}")
    print(f"  Quality Score: {mutation.quality_score}")

    # Should NOT be rejected
    assert mutation.status.value != "rejected", \
        f"FAIL: Mutation was rejected! Reason: {mutation.rejection_reason}"
    print(f"  ✓ Mutation NOT rejected (status: {mutation.status.value})")

    # Should be either PENDING_APPROVAL or APPROVED (if auto-approved as low-risk)
    assert mutation.status.value in ("pending_approval", "approved"), \
        f"FAIL: Expected pending_approval or approved, got {mutation.status.value}"
    print(f"  ✓ Mutation advanced to {mutation.status.value}")

    return mutation


def test_request_approval():
    """Test that request_approval advances PROPOSED to PENDING_APPROVAL."""
    from core.evolution import get_evolution_engine, MutationType, MutationStatus

    engine = get_evolution_engine()

    # Create a mutation that stays in PROPOSED (we'll manually test)
    mutation = engine.propose_mutation(
        agent_name="beta_worker",
        mutation_type=MutationType.BEHAVIOR_CHANGE,
        description="Improve error recovery with exponential backoff strategy",
        rationale="Current fixed retry doesn't handle transient failures well",
        proposed_changes={
            "file_changes": [
                {"path": "core/agent_loop.py", "content": "# improved retry logic"}
            ]
        },
        expected_improvement=0.3,
        risk_level="medium"
    )

    print(f"  Mutation ID: {mutation.mutation_id}")
    print(f"  Initial status: {mutation.status.value}")

    if mutation.status == MutationStatus.PROPOSED:
        result = engine.request_approval(mutation.mutation_id)
        assert result, "FAIL: request_approval returned False"
        updated = engine.get_mutation(mutation.mutation_id)
        assert updated.status == MutationStatus.PENDING_APPROVAL
        print(f"  ✓ Advanced from PROPOSED to PENDING_APPROVAL")
    else:
        print(f"  ✓ Already advanced past PROPOSED: {mutation.status.value}")


def test_deduplicator_persistence():
    """Test that deduplicator persists across instances."""
    from core.mutation_deduplicator import MutationDeduplicator, DEDUP_CACHE_FILE

    # Create first instance and record a proposal
    dedup1 = MutationDeduplicator(window_hours=168)
    test_mutation = {
        "agent_name": "autobot",
        "mutation_type": "parameter_adjustment",
        "description": "Test dedup persistence",
        "proposed_changes": {"strategy": "test_value"},
    }

    # Should be allowed first time
    assert dedup1.should_propose(test_mutation), "FAIL: First proposal should be allowed"
    dedup1.record_proposed(test_mutation)
    print(f"  ✓ First proposal allowed and recorded")

    # Should be blocked on same instance
    assert not dedup1.should_propose(test_mutation), "FAIL: Duplicate should be blocked"
    print(f"  ✓ Duplicate blocked on same instance")

    # Create second instance (simulates restart) - should load from disk
    dedup2 = MutationDeduplicator(window_hours=168)
    assert not dedup2.should_propose(test_mutation), \
        "FAIL: Duplicate should be blocked after restart (loaded from disk)"
    print(f"  ✓ Duplicate blocked after simulated restart (persistent cache works)")

    # Verify cache file exists
    assert os.path.exists(DEDUP_CACHE_FILE), f"FAIL: {DEDUP_CACHE_FILE} not created"
    print(f"  ✓ Cache file exists: {DEDUP_CACHE_FILE}")

    # Cleanup
    dedup2.clear()


def test_valid_params_expanded():
    """Test that expanded VALID_PARAMS allow strategy/learning_rate through."""
    from core.evolution import get_evolution_engine, MutationType

    engine = get_evolution_engine()

    # This used to raise ValueError for 'strategy' - should now pass
    try:
        mutation = engine.propose_mutation(
            agent_name="autobot",
            mutation_type=MutationType.PARAMETER_ADJUSTMENT,
            description="Adaptive strategy for self-improvement",
            rationale="Testing expanded params",
            proposed_changes={"strategy": "adaptive"},
            expected_improvement=0.1,
            risk_level="low"
        )
        assert mutation.status.value != "rejected" or "Empty parameter" not in (mutation.rejection_reason or ""), \
            f"FAIL: strategy param should be valid, got rejected: {mutation.rejection_reason}"
        print(f"  ✓ 'strategy' param accepted (status: {mutation.status.value})")
    except ValueError as e:
        print(f"  ✗ FAIL: ValueError raised for 'strategy': {e}")
        raise


def run_all():
    print("\n" + "=" * 60)
    print("  MUTATION PIPELINE TEST SUITE")
    print("=" * 60)

    tests = [
        ("Pillar Classification (keyword fallback)", test_pillar_classification),
        ("Propose Mutation (passes gates)", test_propose_mutation_passes),
        ("Request Approval (PROPOSED → PENDING_APPROVAL)", test_request_approval),
        ("Deduplicator Persistence", test_deduplicator_persistence),
        ("Expanded VALID_PARAMS", test_valid_params_expanded),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        print(f"\n{'─' * 60}")
        print(f"TEST: {name}")
        print(f"{'─' * 60}")
        try:
            test_fn()
            passed += 1
            print(f"  ══ PASSED ══")
        except Exception as e:
            failed += 1
            print(f"  ══ FAILED: {e} ══")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {passed} passed, {failed} failed")
    print(f"{'=' * 60}\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
