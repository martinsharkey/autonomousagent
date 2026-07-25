import json
import uuid
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from enum import Enum

from governance.audit_log import log_event
from governance.zero_trust import sign_payload, verify_payload
from core.communication import send_message, get_message_bus

EVOLUTION_DIR = "evolution"

class MutationStatus(Enum):
    PROPOSED = "proposed"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    FAILED = "failed"

class MutationType(Enum):
    BEHAVIOR_CHANGE = "behavior_change"
    PROMPT_OPTIMIZATION = "prompt_optimization"
    TOOL_ADDITION = "tool_addition"
    PARAMETER_ADJUSTMENT = "parameter_adjustment"
    STRATEGY_EVOLUTION = "strategy_evolution"

class Mutation:
    def __init__(
        self,
        agent_name: str,
        mutation_type: MutationType,
        description: str,
        rationale: str,
        proposed_changes: Dict[str, Any],
        expected_improvement: float,
        risk_level: str = "medium"
    ):
        self.mutation_id = str(uuid.uuid4())
        self.agent_name = agent_name
        self.mutation_type = mutation_type
        self.description = description
        self.rationale = rationale
        self.proposed_changes = proposed_changes
        self.expected_improvement = expected_improvement
        self.risk_level = risk_level
        self.status = MutationStatus.PROPOSED
        self.timestamp = datetime.utcnow().isoformat()
        self.approval_timestamp = None
        self.implementation_timestamp = None
        self.approved_by = None
        self.rejection_reason = None
        self.implementation_result = None
        self.signature = None
    
    def to_dict(self) -> Dict:
        return {
            "mutation_id": self.mutation_id,
            "agent_name": self.agent_name,
            "mutation_type": self.mutation_type.value,
            "description": self.description,
            "rationale": self.rationale,
            "proposed_changes": self.proposed_changes,
            "expected_improvement": self.expected_improvement,
            "risk_level": self.risk_level,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "approval_timestamp": self.approval_timestamp,
            "implementation_timestamp": self.implementation_timestamp,
            "approved_by": self.approved_by,
            "rejection_reason": self.rejection_reason,
            "implementation_result": self.implementation_result,
            "signature": self.signature
        }
    
    def sign(self):
        payload = self.to_dict()
        self.signature = sign_payload(payload)
        return self
    
    def verify(self) -> bool:
        if not self.signature:
            return False
        payload = self.to_dict()
        return verify_payload(payload, self.signature)
    
    def calculate_hash(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()


class EvolutionEngine:
    def __init__(self):
        self.evolution_dir = Path(EVOLUTION_DIR)
        self.evolution_dir.mkdir(parents=True, exist_ok=True)
        self.mutations_dir = self.evolution_dir / "mutations"
        self.mutations_dir.mkdir(parents=True, exist_ok=True)
        
        self.mutations: Dict[str, Mutation] = {}
        self.mutation_history: List[Dict] = []
        
        self._load_existing_mutations()
    
    def _load_existing_mutations(self):
        for mutation_file in self.mutations_dir.glob("mutation_*.json"):
            try:
                with open(mutation_file, "r") as f:
                    data = json.load(f)
                    mutation = Mutation(
                        agent_name=data["agent_name"],
                        mutation_type=MutationType(data["mutation_type"]),
                        description=data["description"],
                        rationale=data["rationale"],
                        proposed_changes=data["proposed_changes"],
                        expected_improvement=data["expected_improvement"],
                        risk_level=data.get("risk_level", "medium")
                    )
                    mutation.mutation_id = data["mutation_id"]
                    mutation.status = MutationStatus(data["status"])
                    mutation.timestamp = data["timestamp"]
                    mutation.approval_timestamp = data.get("approval_timestamp")
                    mutation.implementation_timestamp = data.get("implementation_timestamp")
                    mutation.approved_by = data.get("approved_by")
                    mutation.rejection_reason = data.get("rejection_reason")
                    mutation.implementation_result = data.get("implementation_result")
                    mutation.signature = data.get("signature")
                    
                    self.mutations[mutation.mutation_id] = mutation
            except Exception as e:
                print(f"[EVOLUTION] Error loading mutation {mutation_file}: {e}")
    
    def propose_mutation(
        self,
        agent_name: str,
        mutation_type: MutationType,
        description: str,
        rationale: str,
        proposed_changes: Dict[str, Any],
        expected_improvement: float,
        risk_level: str = "medium"
    ) -> Mutation:
        mutation = Mutation(
            agent_name=agent_name,
            mutation_type=mutation_type,
            description=description,
            rationale=rationale,
            proposed_changes=proposed_changes,
            expected_improvement=expected_improvement,
            risk_level=risk_level
        )
        mutation.sign()
        
        self.mutations[mutation.mutation_id] = mutation
        self._save_mutation(mutation)
        
        log_event(
            "mutation_proposed",
            agent_name,
            "evolution",
            {
                "mutation_id": mutation.mutation_id,
                "type": mutation_type.value,
                "description": description[:100],
                "risk_level": risk_level
            }
        )
        
        send_message(
            sender=agent_name,
            receiver="human",
            message_type="mutation_proposal",
            content=mutation.to_dict(),
            metadata={"source": "evolution_engine"}
        )
        
        print(f"[EVOLUTION] Mutation proposed by {agent_name}: {mutation.mutation_id}")
        
        return mutation
    
    def request_approval(self, mutation_id: str) -> bool:
        if mutation_id not in self.mutations:
            return False
        
        mutation = self.mutations[mutation_id]
        
        if mutation.status != MutationStatus.PROPOSED:
            return False
        
        mutation.status = MutationStatus.PENDING_APPROVAL
        self._save_mutation(mutation)
        
        log_event(
            "mutation_approval_requested",
            mutation.agent_name,
            "evolution",
            {"mutation_id": mutation_id}
        )
        
        return True
    
    def approve_mutation(self, mutation_id: str, approved_by: str = "human") -> bool:
        if mutation_id not in self.mutations:
            return False
        
        mutation = self.mutations[mutation_id]
        
        if mutation.status not in [MutationStatus.PROPOSED, MutationStatus.PENDING_APPROVAL]:
            return False
        
        mutation.status = MutationStatus.APPROVED
        mutation.approval_timestamp = datetime.utcnow().isoformat()
        mutation.approved_by = approved_by
        self._save_mutation(mutation)
        
        log_event(
            "mutation_approved",
            approved_by,
            "evolution",
            {
                "mutation_id": mutation_id,
                "agent": mutation.agent_name
            }
        )
        
        send_message(
            sender="human",
            receiver=mutation.agent_name,
            message_type="mutation_approved",
            content={"mutation_id": mutation_id, "approved_by": approved_by}
        )
        
        print(f"[EVOLUTION] Mutation approved: {mutation_id}")
        
        return True
    
    def reject_mutation(self, mutation_id: str, reason: str, rejected_by: str = "human") -> bool:
        if mutation_id not in self.mutations:
            return False
        
        mutation = self.mutations[mutation_id]
        
        if mutation.status not in [MutationStatus.PROPOSED, MutationStatus.PENDING_APPROVAL]:
            return False
        
        mutation.status = MutationStatus.REJECTED
        mutation.rejection_reason = reason
        self._save_mutation(mutation)
        
        log_event(
            "mutation_rejected",
            rejected_by,
            "evolution",
            {
                "mutation_id": mutation_id,
                "agent": mutation.agent_name,
                "reason": reason
            }
        )
        
        send_message(
            sender="human",
            receiver=mutation.agent_name,
            message_type="mutation_rejected",
            content={
                "mutation_id": mutation_id,
                "reason": reason,
                "rejected_by": rejected_by
            }
        )
        
        print(f"[EVOLUTION] Mutation rejected: {mutation_id}")
        
        return True
    
    def implement_mutation(self, mutation_id: str) -> Dict[str, Any]:
        if mutation_id not in self.mutations:
            return {"success": False, "error": "Mutation not found"}
        
        mutation = self.mutations[mutation_id]
        
        if mutation.status != MutationStatus.APPROVED:
            return {"success": False, "error": "Mutation not approved"}
        
        try:
            result = self._apply_mutation(mutation)
            
            mutation.status = MutationStatus.IMPLEMENTED
            mutation.implementation_timestamp = datetime.utcnow().isoformat()
            mutation.implementation_result = result
            self._save_mutation(mutation)
            
            log_event(
                "mutation_implemented",
                mutation.agent_name,
                "evolution",
                {
                    "mutation_id": mutation_id,
                    "result": str(result)[:200]
                }
            )
            
            send_message(
                sender=mutation.agent_name,
                receiver="human",
                message_type="mutation_implemented",
                content={
                    "mutation_id": mutation_id,
                    "result": result,
                    "timestamp": mutation.implementation_timestamp
                }
            )
            
            print(f"[EVOLUTION] Mutation implemented: {mutation_id}")
            
            return {"success": True, "result": result}
        
        except Exception as e:
            mutation.status = MutationStatus.FAILED
            mutation.implementation_result = {"error": str(e)}
            self._save_mutation(mutation)
            
            log_event(
                "mutation_failed",
                mutation.agent_name,
                "evolution",
                {
                    "mutation_id": mutation_id,
                    "error": str(e)
                }
            )
            
            return {"success": False, "error": str(e)}
    
    def _apply_mutation(self, mutation: Mutation) -> Dict[str, Any]:
        from core.agent_config import get_config_store
        from core.evaluation import run_evaluation_suite
        
        config_store = get_config_store()
        
        result = {
            "mutation_id": mutation.mutation_id,
            "agent": mutation.agent_name,
            "type": mutation.mutation_type.value,
            "changes_applied": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Get current active config
            current_config = config_store.get_active(mutation.agent_name)
            current_version = current_config.get("version", "v1.0.0")
            
            # Create new version with proposed changes
            new_version = config_store.create_version(
                agent_name=mutation.agent_name,
                changes=mutation.proposed_changes,
                parent_version=current_version,
                mutation_id=mutation.mutation_id
            )
            
            result["changes_applied"].append({
                "type": mutation.mutation_type.value,
                "description": mutation.description,
                "new_version": new_version,
                "parent_version": current_version,
                "status": "created"
            })
            
            # Run evaluation suite
            eval_results = run_evaluation_suite(mutation.agent_name, new_version)
            result["evaluation"] = eval_results
            
            # Check if we should promote
            previous_score = current_config.get("last_eval_score", 0.5)
            new_score = eval_results.get("score", 0.0)
            tolerance = 0.05
            
            if new_score >= previous_score - tolerance:
                config_store.promote(mutation.agent_name, new_version)
                result["promotion"] = "promoted"
                result["score_improvement"] = new_score - previous_score
            else:
                config_store.rollback(mutation.agent_name, current_version)
                result["promotion"] = "rolled_back"
                result["score_regression"] = new_score - previous_score
            
            return result
        
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "failed"
            return result
    
    def _save_mutation(self, mutation: Mutation):
        # Ensure directory exists before writing
        self.mutations_dir.mkdir(parents=True, exist_ok=True)
        
        mutation_file = self.mutations_dir / f"mutation_{mutation.mutation_id}.json"
        with open(mutation_file, "w") as f:
            json.dump(mutation.to_dict(), f, indent=2)
    
    def get_mutation(self, mutation_id: str) -> Optional[Mutation]:
        return self.mutations.get(mutation_id)
    
    def get_agent_mutations(self, agent_name: str, status: MutationStatus = None) -> List[Mutation]:
        mutations = [m for m in self.mutations.values() if m.agent_name == agent_name]
        
        if status:
            mutations = [m for m in mutations if m.status == status]
        
        return sorted(mutations, key=lambda m: m.timestamp, reverse=True)
    
    def get_pending_approvals(self) -> List[Mutation]:
        return [m for m in self.mutations.values() if m.status == MutationStatus.PENDING_APPROVAL]
    
    def get_evolution_stats(self) -> Dict[str, Any]:
        stats = {
            "total_mutations": len(self.mutations),
            "by_status": {},
            "by_agent": {},
            "by_type": {}
        }
        
        for mutation in self.mutations.values():
            status_key = mutation.status.value
            stats["by_status"][status_key] = stats["by_status"].get(status_key, 0) + 1
            
            agent_key = mutation.agent_name
            stats["by_agent"][agent_key] = stats["by_agent"].get(agent_key, 0) + 1
            
            type_key = mutation.mutation_type.value
            stats["by_type"][type_key] = stats["by_type"].get(type_key, 0) + 1
        
        return stats


_evolution_engine = None

def get_evolution_engine() -> EvolutionEngine:
    global _evolution_engine
    if _evolution_engine is None:
        _evolution_engine = EvolutionEngine()
    return _evolution_engine

def propose_mutation(
    agent_name: str,
    mutation_type: MutationType,
    description: str,
    rationale: str,
    proposed_changes: Dict[str, Any],
    expected_improvement: float,
    risk_level: str = "medium"
) -> Mutation:
    engine = get_evolution_engine()
    return engine.propose_mutation(
        agent_name, mutation_type, description, rationale,
        proposed_changes, expected_improvement, risk_level
    )

def approve_mutation(mutation_id: str, approved_by: str = "human") -> bool:
    engine = get_evolution_engine()
    return engine.approve_mutation(mutation_id, approved_by)

def reject_mutation(mutation_id: str, reason: str, rejected_by: str = "human") -> bool:
    engine = get_evolution_engine()
    return engine.reject_mutation(mutation_id, reason, rejected_by)

def implement_mutation(mutation_id: str) -> Dict[str, Any]:
    engine = get_evolution_engine()
    return engine.implement_mutation(mutation_id)

def get_pending_approvals() -> List[Mutation]:
    engine = get_evolution_engine()
    return engine.get_pending_approvals()

def get_evolution_stats() -> Dict[str, Any]:
    engine = get_evolution_engine()
    return engine.get_evolution_stats()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Evolution engine for agent self-modification")
    parser.add_argument("--stats", action="store_true", help="Show evolution statistics")
    parser.add_argument("--pending", action="store_true", help="Show pending approvals")
    parser.add_argument("--agent", help="Show mutations for specific agent")
    
    args = parser.parse_args()
    
    if args.stats:
        stats = get_evolution_stats()
        print(json.dumps(stats, indent=2))
    elif args.pending:
        pending = get_pending_approvals()
        for mutation in pending:
            print(f"\nMutation: {mutation.mutation_id}")
            print(f"  Agent: {mutation.agent_name}")
            print(f"  Type: {mutation.mutation_type.value}")
            print(f"  Description: {mutation.description}")
            print(f"  Expected Improvement: {mutation.expected_improvement}")
    elif args.agent:
        engine = get_evolution_engine()
        mutations = engine.get_agent_mutations(args.agent)
        for mutation in mutations:
            print(f"\nMutation: {mutation.mutation_id}")
            print(f"  Status: {mutation.status.value}")
            print(f"  Type: {mutation.mutation_type.value}")
            print(f"  Description: {mutation.description}")
    else:
        parser.print_help()
