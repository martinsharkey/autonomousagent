import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import patch, Mock
from core.state import AgentState
from governance.consensus import ConsensusEngine
from governance.decision_logger import DecisionLogger
from core.version_store import VersionStore
from core.rollback import RollbackSafetyAssessor

class TestFullMutationCycle:
    @pytest.mark.asyncio
    async def test_full_mutation_cycle(self):
        """
        Scenario: Agent proposes encryption upgrade.
        All three vote YES.
        Tests pass.
        Promotion succeeds.
        Verify state is properly versioned.
        """
        
        consensus = ConsensusEngine(agents=["autobot", "alpha_evaluator", "beta_worker"])
        decision_logger = DecisionLogger()
        version_store = VersionStore()
        
        state = {
            "active_mutation_id": "mut-test-001",
            "proposed_mutation_code": "def encrypt_data(data): return data.encode()",
            "mission_rationale": "Improve data security",
            "council_votes": {"autobot": None, "alpha_evaluator": None, "beta_worker": None},
            "mission_scores": {"autobot": 0.0, "alpha_evaluator": 0.0, "beta_worker": 0.0},
            "loop_count": 0,
            "completed_nodes": []
        }
        
        consensus.create_proposal(
            state["active_mutation_id"],
            "autobot",
            "Encryption upgrade",
            {"code": state["proposed_mutation_code"]}
        )
        
        consensus.cast_vote(state["active_mutation_id"], "autobot", "approve", "Security enhanced")
        consensus.cast_vote(state["active_mutation_id"], "alpha_evaluator", "approve", "Mission aligned")
        consensus.cast_vote(state["active_mutation_id"], "beta_worker", "approve", "Feasible")
        
        result = consensus.check_consensus(state["active_mutation_id"])
        
        assert result == "approved", "Unanimous vote should approve"
        
        decision_logger.log(
            decision_type="TEST_RESULTS",
            metadata={"pass_rate": 0.98, "coverage": 0.95},
            mutation_id=state["active_mutation_id"]
        )
        
        version_id = version_store.save_version(
            code=state["proposed_mutation_code"],
            member_id="autobot",
            mutation_id=state["active_mutation_id"],
            parent_version=None
        )
        
        assert version_id is not None, "Version should be saved"
        
        history = version_store.get_history()
        assert len(history) > 0, "Version history should exist"
        
        decision_logger.log(
            decision_type="MUTATION_PROMOTED",
            metadata={"version_id": version_id},
            mutation_id=state["active_mutation_id"]
        )
        
        audit_trail = decision_logger.get_audit_trail(state["active_mutation_id"])
        assert len(audit_trail) >= 3, "Should have votes, test results, and promotion logged"
    
    @pytest.mark.asyncio
    async def test_rollback_after_regression(self):
        """
        Scenario: Version v1.2.5 causes 300% error increase.
        Autobot detects, proposes rollback.
        Martin approves.
        System rolls back to v1.2.4.
        All three council members resume operations.
        """
        
        version_store = VersionStore()
        decision_logger = DecisionLogger()
        rollback_assessor = RollbackSafetyAssessor()
        
        v1_code = "def process(): return 'v1.2.4'"
        v2_code = "def process(): return 'v1.2.5'"
        
        v1_id = version_store.save_version(
            code=v1_code,
            member_id="autobot",
            mutation_id="mut-v1",
            parent_version=None
        )
        
        v2_id = version_store.save_version(
            code=v2_code,
            member_id="autobot",
            mutation_id="mut-v2",
            parent_version=v1_id
        )
        
        current_state_schema = {
            "messages": list,
            "loop_count": int,
            "encryption_key_cache": dict,
            "active_worker_list": list
        }
        
        target_state_schema = {
            "messages": list,
            "loop_count": int
        }
        
        with patch('core.rollback.load_mllm') as mock_load_mllm:
            mock_model = Mock()
            mock_response = Mock()
            mock_response.content = json.dumps({
                "rollback_safe": True,
                "data_loss_risk": "MINOR",
                "fields_lost": ["encryption_key_cache"],
                "compatibility_issues": [],
                "recommended_actions": ["Reinitialize cache"],
                "operator_approval_required": True
            })
            mock_model.invoke.return_value = mock_response
            mock_load_mllm.return_value = mock_model
            
            assessment = await rollback_assessor.assess_rollback_safety(
                current_version=v2_id,
                target_version=v1_id,
                current_state_schema=current_state_schema,
                target_state_schema=target_state_schema,
                mutation_id="mut-rollback-001"
            )
        
        assert "rollback_safe" in assessment, "Assessment should include safety flag"
        assert "data_loss_risk" in assessment, "Assessment should include data loss risk"
        
        decision_logger.log(
            decision_type="ROLLBACK_APPROVED",
            metadata={
                "current_version": v2_id,
                "target_version": v1_id,
                "assessment": assessment
            },
            mutation_id="mut-rollback-001",
            operator_override="APPROVE"
        )
        
        restored_code = version_store.get_version(v1_id)
        assert restored_code == v1_code, "Should restore v1.2.4 code"
        
        integrity = version_store.verify_integrity(v1_id)
        assert integrity, "Restored version should pass integrity check"
        
        audit_trail = decision_logger.get_audit_trail("mut-rollback-001")
        assert len(audit_trail) >= 2, "Should have safety check and approval logged"
    
    @pytest.mark.asyncio
    async def test_operator_override_promote(self):
        """
        Scenario: Council rejects mutation (2/3 reject).
        Operator overrides and promotes anyway.
        Decision is logged with rationale.
        """
        
        consensus = ConsensusEngine(agents=["autobot", "alpha_evaluator", "beta_worker"])
        decision_logger = DecisionLogger()
        
        proposal_id = "mut-override-001"
        consensus.create_proposal(proposal_id, "autobot", "Test override", {})
        
        consensus.cast_vote(proposal_id, "autobot", "approve", "Security passed")
        consensus.cast_vote(proposal_id, "alpha_evaluator", "reject", "Not aligned")
        consensus.cast_vote(proposal_id, "beta_worker", "reject", "Not feasible")
        
        result = consensus.check_consensus(proposal_id)
        assert result == "rejected", "Council should reject"
        
        decision_logger.log(
            decision_type="OPERATOR_OVERRIDE_PROMOTE",
            metadata={
                "mutation_id": proposal_id,
                "council_votes": {
                    "autobot": True,
                    "alpha_evaluator": False,
                    "beta_worker": False
                }
            },
            mutation_id=proposal_id,
            operator_override="PROMOTE",
            operator_rationale="Operator believes mutation is sound despite dissent"
        )
        
        audit_trail = decision_logger.get_audit_trail(proposal_id)
        override_entries = [e for e in audit_trail if e.get("decision_type") == "OPERATOR_OVERRIDE_PROMOTE"]
        assert len(override_entries) > 0, "Override should be logged"
    
    @pytest.mark.asyncio
    async def test_version_lineage_tracking(self):
        """
        Scenario: Multiple mutations create version chain.
        Verify parent-child relationships are tracked.
        """
        
        version_store = VersionStore()
        
        v1 = version_store.save_version("code_v1", "autobot", "mut-1", None)
        v2 = version_store.save_version("code_v2", "autobot", "mut-2", v1)
        v3 = version_store.save_version("code_v3", "autobot", "mut-3", v2)
        
        lineage = version_store.get_version_lineage(v3)
        
        assert len(lineage) == 3, "Lineage should include all versions"
        assert lineage[0] == v3, "Lineage should start with current version"
        assert lineage[-1] == v1, "Lineage should end with root version"
        
        history = version_store.get_history("autobot")
        assert len(history) >= 3, "Should have at least 3 versions for autobot"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
