import pytest
from governance.consensus import ConsensusEngine

class TestUnanimousVoting:
    def test_unanimous_approval_triggers_tests(self):
        """All three vote YES → must run tests before promotion"""
        engine = ConsensusEngine(agents=["autobot", "alpha_evaluator", "beta_worker"])
        
        proposal_id = "mut-test-001"
        engine.create_proposal(proposal_id, "autobot", "Test mutation", {})
        
        engine.cast_vote(proposal_id, "autobot", "approve", "Security check passed")
        engine.cast_vote(proposal_id, "alpha_evaluator", "approve", "Mission aligned")
        engine.cast_vote(proposal_id, "beta_worker", "approve", "Feasible")
        
        result = engine.check_consensus(proposal_id)
        
        assert result == "approved", "Unanimous vote should approve"
        assert engine.proposals[proposal_id]["status"] == "approved"
    
    def test_dissent_escalates_to_operator(self):
        """One dissent → must escalate, not auto-reject"""
        engine = ConsensusEngine(agents=["autobot", "alpha_evaluator", "beta_worker"])
        
        proposal_id = "mut-test-002"
        engine.create_proposal(proposal_id, "autobot", "Test mutation", {})
        
        engine.cast_vote(proposal_id, "autobot", "approve", "Security check passed")
        engine.cast_vote(proposal_id, "alpha_evaluator", "approve", "Mission aligned")
        engine.cast_vote(proposal_id, "beta_worker", "reject", "Not feasible")
        
        result = engine.check_consensus(proposal_id)
        
        assert result == "rejected", "Mixed votes must reject (not unanimous)"
        assert engine.proposals[proposal_id]["status"] == "rejected"
    
    def test_all_reject(self):
        """All three vote NO → rejected"""
        engine = ConsensusEngine(agents=["autobot", "alpha_evaluator", "beta_worker"])
        
        proposal_id = "mut-test-003"
        engine.create_proposal(proposal_id, "autobot", "Test mutation", {})
        
        engine.cast_vote(proposal_id, "autobot", "reject", "Security risk")
        engine.cast_vote(proposal_id, "alpha_evaluator", "reject", "Not aligned")
        engine.cast_vote(proposal_id, "beta_worker", "reject", "Not feasible")
        
        result = engine.check_consensus(proposal_id)
        
        assert result == "rejected", "All reject should reject"
        assert engine.proposals[proposal_id]["status"] == "rejected"
    
    def test_pending_until_all_vote(self):
        """Not all votes in → pending"""
        engine = ConsensusEngine(agents=["autobot", "alpha_evaluator", "beta_worker"])
        
        proposal_id = "mut-test-004"
        engine.create_proposal(proposal_id, "autobot", "Test mutation", {})
        
        engine.cast_vote(proposal_id, "autobot", "approve", "Security check passed")
        engine.cast_vote(proposal_id, "alpha_evaluator", "approve", "Mission aligned")
        
        result = engine.check_consensus(proposal_id)
        
        assert result == "pending", "Should be pending until all vote"
    
    def test_invalid_agent_cannot_vote(self):
        """Invalid agent cannot cast vote"""
        engine = ConsensusEngine(agents=["autobot", "alpha_evaluator", "beta_worker"])
        
        proposal_id = "mut-test-005"
        engine.create_proposal(proposal_id, "autobot", "Test mutation", {})
        
        result = engine.cast_vote(proposal_id, "invalid_agent", "approve", "Test")
        
        assert result is False, "Invalid agent should not be able to vote"
    
    def test_invalid_vote_value_rejected(self):
        """Invalid vote value should be rejected"""
        engine = ConsensusEngine(agents=["autobot", "alpha_evaluator", "beta_worker"])
        
        proposal_id = "mut-test-006"
        engine.create_proposal(proposal_id, "autobot", "Test mutation", {})
        
        result = engine.cast_vote(proposal_id, "autobot", "invalid_vote", "Test")
        
        assert result is False, "Invalid vote value should be rejected"
    
    def test_two_approve_one_reject_rejects(self):
        """2 approve, 1 reject → rejected (not unanimous)"""
        engine = ConsensusEngine(agents=["autobot", "alpha_evaluator", "beta_worker"])
        
        proposal_id = "mut-test-007"
        engine.create_proposal(proposal_id, "autobot", "Test mutation", {})
        
        engine.cast_vote(proposal_id, "autobot", "approve", "Security check passed")
        engine.cast_vote(proposal_id, "alpha_evaluator", "approve", "Mission aligned")
        engine.cast_vote(proposal_id, "beta_worker", "reject", "Not feasible")
        
        result = engine.check_consensus(proposal_id)
        
        assert result == "rejected", "2/3 approval should reject (requires unanimous)"
    
    def test_one_approve_two_reject_rejects(self):
        """1 approve, 2 reject → rejected"""
        engine = ConsensusEngine(agents=["autobot", "alpha_evaluator", "beta_worker"])
        
        proposal_id = "mut-test-008"
        engine.create_proposal(proposal_id, "autobot", "Test mutation", {})
        
        engine.cast_vote(proposal_id, "autobot", "approve", "Security check passed")
        engine.cast_vote(proposal_id, "alpha_evaluator", "reject", "Not aligned")
        engine.cast_vote(proposal_id, "beta_worker", "reject", "Not feasible")
        
        result = engine.check_consensus(proposal_id)
        
        assert result == "rejected", "1/3 approval should reject"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
