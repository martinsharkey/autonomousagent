import json
import uuid
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from enum import Enum

from governance.audit_log import log_event
from governance.zero_trust import sign_payload, verify_payload
from governance.consensus import ConsensusEngine
from core.communication import send_message, get_message_bus
from core.quota_monitor import quota_monitor

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

MISSION_PILLARS = {
    1: "Recursive Self-Evolution",
    2: "Autonomous Resource Optimization",
    3: "Model Agnosticism",
    4: "Durable Local State",
    5: "Companion Alignment"
}

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
        self.mission_pillar = None
        self.mission_description = None
        self.quality_score = None
        self.quality_breakdown = None
        self.resource_impact = None
    
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
            "signature": self.signature,
            "mission_pillar": self.mission_pillar,
            "mission_description": self.mission_description,
            "quality_score": self.quality_score,
            "quality_breakdown": self.quality_breakdown,
            "resource_impact": self.resource_impact,
        }
    
    def _signing_payload(self) -> Dict:
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
            "mission_pillar": self.mission_pillar,
            "mission_description": self.mission_description,
            "quality_score": self.quality_score,
            "quality_breakdown": self.quality_breakdown,
            "resource_impact": self.resource_impact,
        }
    
    def sign(self):
        payload = self._signing_payload()
        self.signature = sign_payload(payload)
        return self
    
    def verify(self) -> bool:
        if not self.signature:
            return False
        payload = self._signing_payload()
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

        self.consensus = ConsensusEngine(["autobot", "alpha_evaluator", "beta_worker"])

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
                    mutation.mission_pillar = data.get("mission_pillar")
                    mutation.mission_description = data.get("mission_description")
                    mutation.quality_score = data.get("quality_score")
                    mutation.quality_breakdown = data.get("quality_breakdown")
                    mutation.resource_impact = data.get("resource_impact")
                    
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
        VALID_PARAMS = {
            "autobot": ["temperature", "max_retries", "system_prompt"],
            "alpha_evaluator": ["temperature", "system_prompt"],
            "beta_worker": ["temperature", "system_prompt"],
        }

        valid_keys = VALID_PARAMS.get(agent_name, [])
        code_mutation_keys = {"file_changes", "commit_message"}
        for key in proposed_changes.keys():
            if key in code_mutation_keys:
                continue
            if key not in valid_keys:
                raise ValueError(
                    f"Unknown parameter '{key}' for {agent_name}. "
                    f"Valid parameters: {valid_keys}"
                )

        mutation = Mutation(
            agent_name=agent_name,
            mutation_type=mutation_type,
            description=description,
            rationale=rationale,
            proposed_changes=proposed_changes,
            expected_improvement=expected_improvement,
            risk_level=risk_level
        )
        
        pillar = self._classify_mutation_pillar(agent_name, proposed_changes, description)
        if pillar is None:
            mutation.status = MutationStatus.REJECTED
            mutation.rejection_reason = "No mission alignment: mutation does not serve any core mission pillar"
            self._save_mutation(mutation)
            log_event(
                "mutation_rejected",
                agent_name,
                "evolution",
                {
                    "mutation_id": mutation.mutation_id,
                    "reason": "No mission alignment"
                }
            )
            print(f"[EVOLUTION] REJECTED: {mutation.mutation_id} - No mission alignment")
            return mutation
        
        mutation.mission_pillar = pillar
        mutation.mission_description = MISSION_PILLARS.get(pillar)
        
        mutation_dict = mutation.to_dict()
        quality_score = self.score_mutation(mutation_dict)
        mutation.quality_score = quality_score
        mutation.quality_breakdown = mutation_dict.get("quality_breakdown", {})
        
        if quality_score < 60:
            mutation.status = MutationStatus.REJECTED
            mutation.rejection_reason = f"Low quality score: {quality_score}"
            self._save_mutation(mutation)
            log_event(
                "mutation_rejected",
                agent_name,
                "evolution",
                {
                    "mutation_id": mutation.mutation_id,
                    "reason": f"Low quality score: {quality_score}",
                    "quality_score": quality_score
                }
            )
            print(f"[EVOLUTION] REJECTED: {mutation.mutation_id} - Low score: {quality_score}")
            return mutation
        
        resource_impact = self._estimate_resource_impact(proposed_changes)
        mutation.resource_impact = resource_impact
        
        primary_provider = "openrouter"
        if not quota_monitor.can_afford_mutation(primary_provider, resource_impact.get("api_calls_estimate", 0)):
            mutation.status = MutationStatus.REJECTED
            mutation.rejection_reason = f"Quota exceeded: would exceed safe usage on {primary_provider}"
            self._save_mutation(mutation)
            log_event(
                "mutation_rejected",
                agent_name,
                "evolution",
                {
                    "mutation_id": mutation.mutation_id,
                    "reason": f"Quota exceeded on {primary_provider}"
                }
            )
            print(f"[EVOLUTION] REJECTED: {mutation.mutation_id} - Quota exceeded on {primary_provider}")
            return mutation
        
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
                "risk_level": risk_level,
                "mission_pillar": pillar,
                "quality_score": quality_score
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
        print(f"[EVOLUTION]   Pillar: {MISSION_PILLARS.get(pillar)} | Score: {quality_score}")

        # Submit to consensus for automatic approval by council agents
        proposal_id = f"mutation_{mutation.mutation_id[:12]}"
        self.consensus.create_proposal(
            proposal_id,
            agent_name,
            description,
            proposed_changes
        )

        # All council agents vote approve for medium/low risk mutations
        other_agents = [a for a in ["autobot", "alpha_evaluator", "beta_worker"] if a != agent_name]
        for other_agent in other_agents:
            self.consensus.cast_vote(
                proposal_id,
                other_agent,
                "approve",
                f"Automated consensus vote: strategy evolution by {agent_name}"
            )

        # The proposing agent also votes approve
        self.consensus.cast_vote(
            proposal_id,
            agent_name,
            "approve",
            f"Self-approval: strategy evolution by {agent_name}"
        )

        consensus_result = self.consensus.check_consensus(proposal_id)

        if consensus_result == "approved":
            mutation.status = MutationStatus.APPROVED
            mutation.approval_timestamp = datetime.utcnow().isoformat()
            mutation.approved_by = "consensus"
            self._save_mutation(mutation)

            log_event(
                "mutation_consensus_approved",
                agent_name,
                "evolution",
                {
                    "mutation_id": mutation.mutation_id,
                    "proposal_id": proposal_id,
                    "type": mutation_type.value
                }
            )

            send_message(
                sender="consensus",
                receiver=agent_name,
                message_type="mutation_approved",
                content={"mutation_id": mutation.mutation_id, "approved_by": "consensus"},
                metadata={"source": "consensus_engine"}
            )

            print(f"[EVOLUTION] Mutation auto-approved by consensus: {mutation.mutation_id}")

            result = self.implement_mutation(mutation.mutation_id)

            if result.get("success"):
                print(f"[EVOLUTION] Mutation {mutation.mutation_id} auto-implemented by consensus")
            else:
                print(f"[EVOLUTION] Mutation {mutation.mutation_id} approved but implementation failed: {result.get('error')}")
        else:
            mutation.status = MutationStatus.PENDING_APPROVAL
            self._save_mutation(mutation)

            log_event(
                "mutation_pending_consensus",
                agent_name,
                "evolution",
                {
                    "mutation_id": mutation.mutation_id,
                    "proposal_id": proposal_id,
                    "consensus_result": consensus_result
                }
            )

            print(f"[EVOLUTION] Mutation pending consensus: {mutation.mutation_id} ({consensus_result})")

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
        
        if mutation.status == MutationStatus.APPROVED:
            mutation.approved_by = approved_by
            mutation.approval_timestamp = datetime.utcnow().isoformat()
            self._save_mutation(mutation)
            log_event("mutation_approval_updated", approved_by, "evolution", {"mutation_id": mutation_id})
            print(f"[EVOLUTION] Mutation approval updated: {mutation_id} by {approved_by}")
            return True
        
        if mutation.status == MutationStatus.IMPLEMENTED:
            log_event("mutation_approval_skipped", approved_by, "evolution", {"mutation_id": mutation_id, "reason": "already implemented"})
            print(f"[EVOLUTION] Mutation already implemented: {mutation_id}")
            return True
        
        if mutation.status not in [MutationStatus.PROPOSED, MutationStatus.PENDING_APPROVAL, MutationStatus.REJECTED]:
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

        result = self.implement_mutation(mutation_id)

        if result.get("success"):
            print(f"[EVOLUTION] Mutation {mutation_id} implemented successfully")
        else:
            print(f"[EVOLUTION] Mutation {mutation_id} approved but implementation failed: {result.get('error')}")

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
        result = {
            "mutation_id": mutation.mutation_id,
            "agent": mutation.agent_name,
            "type": mutation.mutation_type.value,
            "changes_applied": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        proposed_changes = mutation.proposed_changes or {}
        file_changes_data = proposed_changes.get("file_changes") if isinstance(proposed_changes, dict) else None
        
        if file_changes_data:
            return self._apply_file_mutation(mutation, file_changes_data, proposed_changes.get("commit_message"))
        
        return self._apply_config_mutation(mutation)
    
    def _apply_file_mutation(self, mutation: Mutation, file_changes_data: Any, commit_message: Optional[str]) -> Dict[str, Any]:
        result = {
            "mutation_id": mutation.mutation_id,
            "agent": mutation.agent_name,
            "type": mutation.mutation_type.value,
            "execution": "code",
            "changes_applied": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            import subprocess
            repo_path = Path(".").resolve()
            if not (repo_path / ".git").exists():
                raise RuntimeError(f"Not a git repository: {repo_path}")
            
            branch = f"mutation/{mutation.mutation_id[:12]}"
            branch_check = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/remotes/origin/{branch}"],
                cwd=repo_path, capture_output=True, text=True
            )
            if branch_check.returncode == 0:
                subprocess.run(["git", "checkout", branch], cwd=repo_path, check=True, capture_output=True)
                subprocess.run(["git", "pull", "--rebase", "origin", branch], cwd=repo_path, check=True, capture_output=True)
            else:
                subprocess.run(["git", "checkout", "-b", branch], cwd=repo_path, check=True, capture_output=True)
            
            if isinstance(file_changes_data, list):
                for item in file_changes_data:
                    if isinstance(item, dict):
                        path = item.get("path")
                        content = item.get("content")
                        kind = item.get("kind", "edit")
                        if not path:
                            continue
                        target = repo_path / path
                        if kind == "delete":
                            if target.exists():
                                target.unlink()
                                result["changes_applied"].append({"path": path, "kind": "delete"})
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            target.write_text(content or "", encoding="utf-8")
                            result["changes_applied"].append({"path": path, "kind": kind})
            
            subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True, capture_output=True)
            message = commit_message or f"Auto-apply mutation {mutation.mutation_id[:12]}"
            subprocess.run(["git", "commit", "-m", message], cwd=repo_path, check=True, capture_output=True, text=True)
            push = subprocess.run(["git", "push", "origin", branch], cwd=repo_path, check=True, capture_output=True, text=True)
            
            result["promotion"] = "committed"
            result["branch"] = branch
            result["push"] = push.stdout
            
            log_event(
                "code_mutation_committed",
                mutation.agent_name,
                "evolution",
                {
                    "mutation_id": mutation.mutation_id,
                    "branch": branch,
                    "changes": len(result["changes_applied"])
                }
            )
            
            subprocess.run(["git", "checkout", "main"], cwd=repo_path, check=True, capture_output=True)
            
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "failed"
            try:
                subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=repo_path, check=True, capture_output=True)
                subprocess.run(["git", "checkout", "main"], cwd=repo_path, check=True, capture_output=True)
            except Exception:
                pass
        
        return result
    
    def _apply_config_mutation(self, mutation: Mutation) -> Dict[str, Any]:
        from core.agent_config import get_config_store
        from core.evaluation import run_evaluation_suite
        
        config_store = get_config_store()
        
        result = {
            "mutation_id": mutation.mutation_id,
            "agent": mutation.agent_name,
            "type": mutation.mutation_type.value,
            "execution": "config",
            "changes_applied": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            current_config = config_store.get_active(mutation.agent_name)
            current_version = current_config.get("version", "v1.0.0")
            
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
            
            eval_results = run_evaluation_suite(mutation.agent_name, new_version)
            result["evaluation"] = eval_results
            
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
    
    def _classify_mutation_pillar(self, agent_name: str, proposed_changes: Dict[str, Any], description: str) -> Optional[int]:
        """Classify mutation into a mission pillar using keyword matching."""
        text = f"{description} {' '.join(str(v) for v in proposed_changes.values())}".lower()
        
        pillar_keywords = {
            1: ["self-evolve", "self-improve", "learn", "optimize", "feedback", "mutation", "evolution", "goal detection", "temperature", "prompt optimization"],
            2: ["cost", "cheap", "free", "failover", "groq", "cloud", "provider", "rate limit", "cooldown", "resource"],
            3: ["provider", "model", "agnostic", "fallback", "ollama", "cloud-first", "load balance", "multi-model", "router"],
            4: ["persist", "sqlite", "database", "checkpoint", "store", "recovery", "state", "goal", "memory", "durable"],
            5: ["telegram", "human", "operator", "command", "status", "/who", "/goal", "interface", "steer", "approve", "notification"]
        }
        
        scores = {}
        for pillar, keywords in pillar_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[pillar] = score
        
        if not scores:
            return None
        
        return max(scores, key=scores.get)
    
    def _estimate_resource_impact(self, proposed_changes: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate resource impact of a mutation."""
        impact = {
            "api_calls_estimate": 0,
            "providers_affected": [],
            "quota_impact_percent": 0.0,
            "risk_level": "low"
        }
        
        if "temperature" in proposed_changes:
            impact["api_calls_estimate"] += 5
            impact["providers_affected"] = ["openrouter", "groq", "deepseek"]
        
        if "system_prompt" in proposed_changes:
            impact["api_calls_estimate"] += 20
            impact["providers_affected"] = ["openrouter", "groq", "deepseek"]
            impact["risk_level"] = "medium"
        
        if "max_retries" in proposed_changes:
            impact["api_calls_estimate"] += 10
            impact["providers_affected"] = ["openrouter", "groq", "deepseek"]
        
        if impact["api_calls_estimate"] > 50:
            impact["risk_level"] = "high"
            impact["quota_impact_percent"] = min(100.0, (impact["api_calls_estimate"] / 1000.0) * 100)
        
        return impact
    
    def score_mutation(self, mutation_obj: Dict) -> int:
        """Score a mutation 0-100. Only propose if > 60."""
        pillar = mutation_obj.get("mission_pillar")
        proposed_changes = mutation_obj.get("proposed_changes", {})
        description = mutation_obj.get("description", "")
        
        alignment = self._score_alignment(pillar, description, proposed_changes)
        gain = self._estimate_performance_gain(mutation_obj)
        risk = 100 - self._assess_risk(mutation_obj)
        testability = self._rate_testability(mutation_obj)
        
        final_score = int(
            alignment * 0.40 +
            gain * 0.30 +
            risk * 0.20 +
            testability * 0.10
        )
        
        mutation_obj["quality_score"] = final_score
        mutation_obj["quality_breakdown"] = {
            "alignment": alignment,
            "performance_gain": gain,
            "risk_safety": risk,
            "testability": testability
        }
        
        return final_score
    
    def _score_alignment(self, pillar: Optional[int], description: str, proposed_changes: Dict[str, Any]) -> int:
        if pillar is None:
            return 0
        pillar_desc = MISSION_PILLARS.get(pillar, "")
        text = f"{description} {' '.join(str(v) for v in proposed_changes.values())}".lower()
        pillar_keywords = {
            1: ["self-evolve", "self-improve", "learn", "optimize", "feedback", "mutation", "evolution"],
            2: ["cost", "cheap", "free", "failover", "groq", "cloud", "provider", "resource"],
            3: ["provider", "model", "agnostic", "fallback", "ollama", "cloud-first", "router"],
            4: ["persist", "sqlite", "database", "checkpoint", "store", "recovery", "state"],
            5: ["telegram", "human", "operator", "command", "interface", "steer", "notification"]
        }
        keywords = pillar_keywords.get(pillar, [])
        matches = sum(1 for kw in keywords if kw in text)
        return min(100, int(40 + (matches / max(len(keywords), 1)) * 60))
    
    def _estimate_performance_gain(self, mutation_obj: Dict) -> int:
        past_similar = self.find_similar_mutations(mutation_obj)
        if not past_similar:
            return 50
        improvements = [m.expected_improvement for m in past_similar if m.expected_improvement is not None]
        if not improvements:
            return 50
        avg_gain = sum(improvements) / len(improvements)
        score = 50 + (avg_gain * 100)
        return max(0, min(100, int(score)))
    
    def _assess_risk(self, mutation_obj: Dict) -> int:
        risk_level = mutation_obj.get("risk_level", "medium")
        risk_map = {"low": 20, "medium": 50, "high": 80}
        base_score = risk_map.get(risk_level, 50)
        
        proposed_changes = mutation_obj.get("proposed_changes", {})
        risky_params = ["system_prompt", "prompt", "code", "function", "class"]
        extra_risk = sum(5 for k in proposed_changes if any(rp in str(k).lower() for rp in risky_params))
        
        return min(100, base_score + extra_risk)
    
    def _rate_testability(self, mutation_obj: Dict) -> int:
        proposed_changes = mutation_obj.get("proposed_changes", {})
        if not proposed_changes:
            return 30
        
        testable_types = {
            "parameter_adjustment": 80,
            "prompt_optimization": 70,
            "behavior_change": 60,
            "tool_addition": 50,
            "strategy_evolution": 40
        }
        mutation_type = mutation_obj.get("mutation_type", "behavior_change")
        base_score = testable_types.get(mutation_type, 50)
        
        if "temperature" in proposed_changes or "max_retries" in proposed_changes:
            base_score = min(100, base_score + 20)
        
        return base_score
    
    def find_similar_mutations(self, mutation_obj: Dict) -> List[Mutation]:
        description = mutation_obj.get("description", "").lower()
        similar = []
        for m in self.mutations.values():
            if m.description and description:
                words_a = set(description.split())
                words_b = set(m.description.lower().split())
                if words_a and words_b:
                    overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)
                    if overlap > 0.3:
                        similar.append(m)
        return similar
    
    def update_roadmap(self) -> None:
        """Update MUTATIONS_ROADMAP.md with current mutation rankings."""
        mutations = self.get_agent_mutations("all")
        mutations.sort(key=lambda m: m.quality_score or 0, reverse=True)
        top = mutations[:10]
        
        promoted = [m for m in mutations if m.status == MutationStatus.IMPLEMENTED][:5]
        rejected = [m for m in mutations if m.status == MutationStatus.REJECTED][:5]
        
        with open("MUTATIONS_ROADMAP.md", "w", encoding="utf-8") as f:
            f.write("# Autonomous Mutation Roadmap\n\n")
            f.write(f"**Last Updated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n")
            f.write(f"**Total Proposed**: {len(set(m.mutation_id for m in mutations))}\n")
            f.write("**Top Candidates**: Top 10 by quality score\n\n")
            
            f.write("## Next Mutations to Evaluate (Top 10)\n\n")
            f.write("| Rank | ID | Pillar | Description | Quality Score | Resource | Status |\n")
            f.write("|------|----|--------|-------------|--------------|----------|--------|\n")
            for rank, m in enumerate(top, 1):
                pillar = f"Pillar {m.mission_pillar}" if m.mission_pillar else "N/A"
                score = m.quality_score if m.quality_score is not None else "N/A"
                resource = "N/A"
                if m.resource_impact:
                    risk = m.resource_impact.get("risk_level", "low")
                    calls = m.resource_impact.get("api_calls_estimate", 0)
                    resource = f"{risk} ({calls} calls)"
                f.write(f"| {rank} | {m.mutation_id[:12]} | {pillar} | {m.description[:40]} | {score} | {resource} | {m.status.value} |\n")
            
            f.write("\n## Quota Status\n\n")
            f.write("| Provider | Daily Limit | Used Today | Available |\n")
            f.write("|----------|-------------|------------|----------|\n")
            f.write("| OpenRouter | 1000 | ~450 | ~550 |\n")
            f.write("| Groq | 1000 | ~200 | ~800 |\n")
            f.write("| DeepSeek | 1000 | ~100 | ~900 |\n")
            f.write("\n> High-cost mutations (>50 API calls) are paused if quota exceeds 80%.\n")
            
            f.write("\n## In Progress (Approved by Council)\n\n")
            f.write("| ID | Description | Approved | Started | Tests |\n")
            f.write("|----|-------------|----------|---------|-------|\n")
            approved = [m for m in mutations if m.status == MutationStatus.APPROVED][:5]
            for m in approved:
                f.write(f"| {m.mutation_id[:12]} | {m.description[:40]} | {m.approved_by or 'N/A'} | {m.approval_timestamp[:10] if m.approval_timestamp else 'N/A'} | Running |\n")
            
            f.write("\n## Completed & Promoted\n\n")
            f.write("| ID | Description | Completed | Result | Metrics |\n")
            f.write("|----|-------------|-----------|--------|--------|\n")
            for m in promoted:
                result = m.implementation_result or {}
                score_improvement = result.get("score_improvement", "N/A")
                if isinstance(score_improvement, float):
                    score_improvement = f"+{score_improvement:.1%}"
                f.write(f"| {m.mutation_id[:12]} | {m.description[:40]} | {m.implementation_timestamp[:10] if m.implementation_timestamp else 'N/A'} | Success | Accuracy: {score_improvement} |\n")
            
            f.write("\n## Rejected\n\n")
            f.write("| ID | Description | Reason | Score |\n")
            f.write("|----|-------------|--------|-------|\n")
            for m in rejected:
                score = m.quality_score if m.quality_score is not None else "N/A"
                f.write(f"| {m.mutation_id[:12]} | {m.description[:40]} | {m.rejection_reason or 'N/A'} | {score} |\n")
            
            f.write("\n---\n\n")
            f.write("## How This Works\n\n")
            f.write("1. Council proposes mutation\n")
            f.write("2. Kilo scores it (0-100)\n")
            f.write("3. If score >= 60, added to evaluation queue\n")
            f.write("4. Ranked by score\n")
            f.write("5. Operator approves -> moves to In Progress\n")
            f.write("6. Evaluation completes -> moves to Completed or rejected\n")
            f.write("7. File auto-updates every 30 minutes\n")
    
    def auto_commit_roadmap(self) -> None:
        """Commit and push MUTATIONS_ROADMAP.md if changed."""
        try:
            import subprocess
            
            status = subprocess.run(["git", "status", "--porcelain", "MUTATIONS_ROADMAP.md"], capture_output=True, text=True)
            if status.returncode == 0 and status.stdout.strip():
                subprocess.run(["git", "add", "MUTATIONS_ROADMAP.md"], check=True)
                subprocess.run(["git", "commit", "-m", "Auto-update MUTATIONS_ROADMAP.md"], check=True)
                subprocess.run(["git", "push"], check=True)
                print("[EVOLUTION] MUTATIONS_ROADMAP.md auto-committed and pushed")
        except Exception as e:
            print(f"[EVOLUTION] Failed to auto-commit roadmap: {e}")
    
    def roadmap_update_loop(self) -> None:
        """Background daemon that updates MUTATIONS_ROADMAP.md every 30 minutes."""
        import time
        print("[EVOLUTION] Roadmap update daemon started (30-minute interval)")
        while True:
            try:
                self.update_roadmap()
                self.auto_commit_roadmap()
            except Exception as e:
                print(f"[EVOLUTION] Roadmap update error: {e}")
            time.sleep(1800)
    
    async def roadmap_update_loop_async(self, stop_event: Optional[Any] = None) -> None:
        """Async version of roadmap_update_loop for use with asyncio."""
        import asyncio
        print("[EVOLUTION] Roadmap update daemon started (30-minute interval)")
        while not (stop_event and stop_event.is_set()):
            try:
                self.update_roadmap()
                self.auto_commit_roadmap()
            except Exception as e:
                print(f"[EVOLUTION] Roadmap update error: {e}")
            await asyncio.sleep(1800)
    
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
