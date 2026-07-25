"""Tests for dynamic reward calculation."""

import pytest
from core.agent_loop import calculate_reward


class TestCalculateReward:
    """Test that rewards vary based on feedback."""
    
    def test_reward_varies_with_good_feedback(self):
        """Good feedback should produce higher reward."""
        feedback = {"success_rate": 0.9, "speed_bonus": 0.1}
        reward = calculate_reward(feedback)
        
        assert reward > 0.5, f"Good feedback should produce reward > 0.5, got {reward}"
        assert reward == pytest.approx(0.66, rel=0.01), f"Expected ~0.66, got {reward}"
    
    def test_reward_varies_with_bad_feedback(self):
        """Bad feedback should produce lower reward."""
        feedback = {"success_rate": 0.1, "speed_bonus": 0.0}
        reward = calculate_reward(feedback)
        
        assert reward < 0.5, f"Bad feedback should produce reward < 0.5, got {reward}"
        assert reward == pytest.approx(0.07, rel=0.01), f"Expected ~0.07, got {reward}"
    
    def test_reward_default_is_neutral(self):
        """No feedback should produce neutral reward."""
        reward = calculate_reward(None)
        
        assert reward == 0.5, f"Default reward should be 0.5, got {reward}"
    
    def test_reward_range_is_valid(self):
        """Reward should always be between 0.0 and 1.0."""
        # Test extreme values
        feedback_max = {"success_rate": 1.0, "speed_bonus": 1.0}
        reward_max = calculate_reward(feedback_max)
        assert 0.0 <= reward_max <= 1.0, f"Reward should be in [0, 1], got {reward_max}"
        
        feedback_min = {"success_rate": 0.0, "speed_bonus": 0.0}
        reward_min = calculate_reward(feedback_min)
        assert 0.0 <= reward_min <= 1.0, f"Reward should be in [0, 1], got {reward_min}"
    
    def test_good_reward_higher_than_bad(self):
        """Good feedback should always produce higher reward than bad."""
        good_feedback = {"success_rate": 0.9, "speed_bonus": 0.1}
        bad_feedback = {"success_rate": 0.1, "speed_bonus": 0.0}
        
        reward_good = calculate_reward(good_feedback)
        reward_bad = calculate_reward(bad_feedback)
        
        assert reward_good > reward_bad, f"Good reward ({reward_good}) should be > bad reward ({reward_bad})"
    
    def test_reward_not_hardcoded(self):
        """Rewards should NOT all be 0.5."""
        feedbacks = [
            {"success_rate": 0.9, "speed_bonus": 0.1},
            {"success_rate": 0.1, "speed_bonus": 0.0},
            {"success_rate": 0.5, "speed_bonus": 0.5},
        ]
        
        rewards = [calculate_reward(f) for f in feedbacks]
        
        # At least one should not be 0.5
        assert not all(r == 0.5 for r in rewards), "All rewards are 0.5 - calculation is broken!"
        
        # Should have variation
        assert len(set(rewards)) > 1, "All rewards are identical - no variation!"
