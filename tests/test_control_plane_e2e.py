"""
Integration Tests for Control Plane

This module tests the core autonomous control plane:
1. Goal creation and persistence (SQLite durability)
2. Goal status lifecycle (pending → in_progress → completed)
3. Goal priority ordering (high priority first)
4. Autonomy level risk gating (SAFE/LIMITED/FULL)
5. Health check system

These tests verify the control plane works end-to-end
without requiring the full daemon to be running.
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest


def test_goal_creation_and_persistence():
    """Test creating a goal and verifying it persists."""
    from core.goals import GoalStore
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "goals_test.db"
        
        store1 = GoalStore(db_path=str(db_path))
        goal_id = store1.create_goal(
            description="Test goal",
            priority=10,
            source="test"
        )
        assert goal_id is not None
        
        goal = store1.get_goal(goal_id)
        assert goal is not None
        assert goal["description"] == "Test goal"
        assert goal["status"] == "pending"
        
        store2 = GoalStore(db_path=str(db_path))
        restored_goal = store2.get_goal(goal_id)
        
        assert restored_goal is not None
        assert restored_goal["description"] == "Test goal"
        print("✓ Goal creation and persistence works")


def test_goal_status_updates():
    """Test updating goal status."""
    from core.goals import GoalStore
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "goals_test.db"
        store = GoalStore(db_path=str(db_path))
        
        goal_id = store.create_goal(
            description="Test status",
            priority=5,
            source="test"
        )
        
        store.update_goal_status(goal_id, "in_progress")
        goal = store.get_goal(goal_id)
        assert goal["status"] == "in_progress"
        
        store.update_goal_status(goal_id, "completed", result_summary="Done", reward=0.9)
        goal = store.get_goal(goal_id)
        assert goal["status"] == "completed"
        assert goal["reward"] == 0.9
        print("✓ Goal status updates work")


def test_goal_priority_ordering():
    """Test goals are ordered by priority."""
    from core.goals import GoalStore
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "goals_test.db"
        store = GoalStore(db_path=str(db_path))
        
        store.create_goal("Low priority", priority=1, source="test")
        store.create_goal("High priority", priority=10, source="test")
        store.create_goal("Medium priority", priority=5, source="test")
        
        pending = store.get_pending_goals()
        
        assert pending[0]["priority"] == 10
        assert pending[1]["priority"] == 5
        assert pending[2]["priority"] == 1
        print("✓ Goal priority ordering works")


def test_autonomy_levels_gating():
    """Test autonomy levels gate mutations."""
    from core.autonomy_levels import AutonomyController, AutonomyLevel
    
    controller_safe = AutonomyController(AutonomyLevel.SAFE)
    assert controller_safe.can_mutate("low") == False
    
    controller_limited = AutonomyController(AutonomyLevel.LIMITED)
    assert controller_limited.can_mutate("low") == True
    assert controller_limited.can_mutate("high") == False
    
    controller_full = AutonomyController(AutonomyLevel.FULL)
    assert controller_full.can_mutate("high") == True
    print("✓ Autonomy level gating works")


def test_health_check_passes():
    """Test health check system."""
    from core.health import generate_health_report
    
    result = generate_health_report()
    
    assert isinstance(result, dict)
    assert "timestamp" in result
    assert "loops" in result
    assert "checkpointer" in result
    print("✓ Health check works")


if __name__ == "__main__":
    test_goal_creation_and_persistence()
    test_goal_status_updates()
    test_goal_priority_ordering()
    test_autonomy_levels_gating()
    test_health_check_passes()
    print("\n✓ All integration tests passed")
