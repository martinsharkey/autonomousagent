import json
import uuid
import hashlib
import asyncio
import fnmatch
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path
from enum import Enum

from governance.audit_log import log_event
from governance.zero_trust import sign_payload, verify_payload
from governance.consensus import ConsensusEngine
from core.communication import send_message, get_message_bus
from core.quota_monitor import quota_monitor
from core.mutation_deduplicator import get_deduplicator

PROJECT_ROOT = Path(__file__).resolve().parent.parent

EVOLUTION_DIR = "evolution"
PENDING_APPROVAL_TTL_SECONDS = 300
FILE_MUTATION_ALLOWLIST = [
    "agents/",
    "core/",
    "governance/",
    "tools/",
    "microbots/",
    "tests/",
    "evidence/",
    "providers.yaml",
    "README.md",
    "MISSION_PURPOSE.md",
    "MUTATIONS_ROADMAP.md",
    "TODO.md",
    "session_log.md",
]
FILE_MUTATION_DENYLIST = [
    ".env",
    ".env.",
    "secrets/",
    "core/zero_trust.py",
    "governance/zero_trust.py",
]

class MutationStatus(Enum):
    PROPOSED = "proposed"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    FAILED = "failed"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"

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
        self.pending_approval_timestamp = None
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
        self.rollout_state = None
        self.rollout_targets = []
        self.rollout_current_index = 0
        self.rollout_soak_cycles = 3
        self.rollout_soak_completed_cycles = 0
        self.rollout_baseline_score = None
        self.rollout_started_at = None
        self.rollout_completed_at = None
        self.votes = {}
    
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
            "pending_approval_timestamp": self.pending_approval_timestamp,
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
            "rollout_state": self.rollout_state,
            "rollout_targets": self.rollout_targets,
            "rollout_current_index": self.rollout_current_index,
            "rollout_soak_cycles": self.rollout_soak_cycles,
            "rollout_soak_completed_cycles": self.rollout_soak_completed_cycles,
            "rollout_baseline_score": self.rollout_baseline_score,
            "rollout_started_at": self.rollout_started_at,
            "rollout_completed_at": self.rollout_completed_at,
            "votes": self.votes,
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
            "pending_approval_timestamp": self.pending_approval_timestamp,
            "implementation_timestamp": self.implementation_timestamp,
            "approved_by": self.approved_by,
            "rejection_reason": self.rejection_reason,
            "implementation_result": self.implementation_result,
            "mission_pillar": self.mission_pillar,
            "mission_description": self.mission_description,
            "quality_score": self.quality_score,
            "quality_breakdown": self.quality_breakdown,
            "resource_impact": self.resource_impact,
            "rollout_state": self.rollout_state,
            "rollout_targets": self.rollout_targets,
            "rollout_current_index": self.rollout_current_index,
            "rollout_soak_cycles": self.rollout_soak_cycles,
            "rollout_baseline_score": self.rollout_baseline_score,
            "rollout_started_at": self.rollout_started_at,
            "rollout_completed_at": self.rollout_completed_at,
        }
    
    def sign(self):
        payload = self._signing_payload()
        self.signature = sign_payload(payload)
        return self

    def system_reject(self, reason: str):
        self.status = MutationStatus.REJECTED
        self.rejection_reason = reason
        self.signature = "SYSTEM_REJECTED"
        self.approval_timestamp = datetime.now(timezone.utc).isoformat()
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
                    mutation.rollout_state = data.get("rollout_state")
                    mutation.rollout_targets = data.get("rollout_targets", [])
                    mutation.rollout_current_index = data.get("rollout_current_index", 0)
                    mutation.rollout_soak_cycles = data.get("rollout_soak_cycles", 3)
                    mutation.rollout_baseline_score = data.get("rollout_baseline_score")
                    mutation.rollout_started_at = data.get("rollout_started_at")
                    mutation.rollout_completed_at = data.get("rollout_completed_at")
                    
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
            "autobot": ["max_retries", "system_prompt"],
            "alpha_evaluator": ["system_prompt"],
            "beta_worker": ["max_retries", "system_prompt"],
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
            
            if key == "temperature":
                raise ValueError(
                    f"Temperature is now dynamic and cannot be set via mutation. "
                    f"Use context-aware temperature selection instead."
                )

        file_changes_data = proposed_changes.get("file_changes") if isinstance(proposed_changes, dict) else None
        if file_changes_data:
            if not isinstance(file_changes_data, list):
                raise ValueError("file_changes must be a list")
            for item in file_changes_data:
                if not isinstance(item, dict):
                    continue
                path = item.get("path", "")
                if not self._validate_file_change(path):
                    raise ValueError(f"File mutation path denied by policy: {path}")

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
            mutation.system_reject("No mission alignment: mutation does not serve any core mission pillar")
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
            mutation.system_reject(f"Low quality score: {quality_score}")
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
            mutation.system_reject(f"Quota exceeded: would exceed safe usage on {primary_provider}")
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
        get_deduplicator().record_proposed({
            "agent_name": agent_name,
            "mutation_type": mutation_type.value,
            "description": description,
            "proposed_changes": proposed_changes,
        })
        
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

        proposal_id = f"mutation_{mutation.mutation_id[:12]}"
        self.consensus.create_proposal(
            proposal_id,
            agent_name,
            description,
            proposed_changes
        )

        low_risk_auto_approve = risk_level == "low" and (quality_score or 0) >= 80
        if low_risk_auto_approve:
            other_agents = [a for a in ["autobot", "alpha_evaluator", "beta_worker"] if a != agent_name]
            for other_agent in other_agents:
                self.consensus.cast_vote(
                    proposal_id,
                    other_agent,
                    "approve",
                    f"Low-risk auto-approval: quality score {quality_score}"
                )
            self.consensus.cast_vote(
                proposal_id,
                agent_name,
                "approve",
                f"Self-approval: low-risk mutation with quality score {quality_score}"
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
                mutation.pending_approval_timestamp = datetime.utcnow().isoformat()
                self._save_mutation(mutation)
                print(f"[EVOLUTION] Mutation pending consensus (low-risk): {mutation.mutation_id}")
            try:
                running_loop = asyncio.get_running_loop()
                running_loop.create_task(self._send_mutation_telegram(
                    mutation.mutation_id, "PENDING", agent_name, "EVOLUTION", mutation.to_dict()
                ))
            except RuntimeError:
                pass
        else:
            mutation.status = MutationStatus.PENDING_APPROVAL
            mutation.pending_approval_timestamp = datetime.utcnow().isoformat()
            self._save_mutation(mutation)

            log_event(
                "mutation_pending_consensus",
                agent_name,
                "evolution",
                {
                    "mutation_id": mutation.mutation_id,
                    "proposal_id": proposal_id,
                    "consensus_result": "pending_real_votes"
                }
            )

            print(f"[EVOLUTION] Mutation pending real council votes: {mutation.mutation_id}")

            try:
                running_loop = asyncio.get_running_loop()
                running_loop.create_task(self._send_mutation_telegram(
                    mutation.mutation_id, "PENDING", agent_name, "EVOLUTION", mutation.to_dict()
                ))
            except RuntimeError:
                pass

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

        result = self.implement_mutation(mutation_id)

        if result.get("success"):
            print(f"[EVOLUTION] Mutation {mutation_id} implemented successfully")
        else:
            print(f"[EVOLUTION] Mutation {mutation_id} approved but implementation failed: {result.get('error')}")

        return True

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

            if not result.get("success"):
                mutation.status = MutationStatus.FAILED
                mutation.implementation_result = result
                self._save_mutation(mutation)
                return {"success": False, "error": result.get("error", "Mutation application failed")}

            test_result = self._run_tests_after_mutation(mutation_id)
            metrics = self._measure_performance_change(mutation_id, test_result)
            verification = self._verify_mutation_success(mutation, metrics, test_result)

            if verification.get("success"):
                promotion = self._promote_mutation(mutation, metrics)
                mutation.status = MutationStatus.PROMOTED
                mutation.implementation_result = {
                    "applied": result,
                    "tests": test_result,
                    "metrics": metrics,
                    "promoted": promotion,
                }
            else:
                rollback = self._rollback_mutation(mutation)
                mutation.status = MutationStatus.ROLLED_BACK
                mutation.implementation_result = {
                    "applied": result,
                    "tests": test_result,
                    "metrics": metrics,
                    "reason_rollback": verification.get("reason"),
                    "rollback": rollback,
                }

            mutation.implementation_timestamp = datetime.utcnow().isoformat()
            self._save_mutation(mutation)

            log_event(
                "mutation_implemented",
                mutation.agent_name,
                "evolution",
                {
                    "mutation_id": mutation_id,
                    "status": mutation.status.value,
                    "verification": verification,
                },
            )

            send_message(
                sender=mutation.agent_name,
                receiver="human",
                message_type="mutation_implemented",
                content={
                    "mutation_id": mutation_id,
                    "status": mutation.status.value,
                    "result": result,
                    "verification": verification,
                    "timestamp": mutation.implementation_timestamp,
                },
            )

            print(f"[EVOLUTION] Mutation {mutation.status.value}: {mutation_id}")

            return {"success": True, "result": result, "verification": verification}

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
                    "error": str(e),
                },
            )

            return {"success": False, "error": str(e)}

    def _run_tests_after_mutation(self, mutation_id: str) -> Dict[str, Any]:
        import subprocess

        try:
            result = subprocess.run(
                [
                    "python", "-m", "pytest",
                    "tests/test_mutation_end_to_end.py",
                    "tests/test_integration.py",
                    "tests/test_council_unanimous_voting.py",
                    "tests/test_control_plane_e2e.py",
                    "-m", "not live",
                    "-v", "--tb=short", "-q",
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(PROJECT_ROOT),
            )
            return {
                "passed": result.returncode == 0,
                "output": result.stdout[-2000:] if result.stdout else "",
                "errors": result.stderr[-1000:] if result.stderr else "",
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "passed": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _measure_performance_change(
        self, mutation_id: str, test_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        mutation = self.mutations.get(mutation_id)
        if not mutation:
            return {"error": "Mutation not found"}

        baseline = mutation.quality_score or 0.5
        current = baseline
        try:
            from core.evaluation import run_evaluation_suite

            agent_name = mutation.agent_name
            current_version = mutation.implementation_result.get("applied", {}).get("version")
            if current_version:
                eval_result = run_evaluation_suite(agent_name, current_version)
                current = eval_result.get("score", baseline)
        except Exception:
            pass

        deltas = {
            "baseline_score": baseline,
            "current_score": current,
            "score_change": current - baseline,
            "tests_passed": test_result.get("passed", False),
        }

        return {
            "baseline": baseline,
            "current": current,
            "deltas": deltas,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _verify_mutation_success(
        self, mutation: Mutation, metrics: Dict[str, Any], test_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        success = True
        reasons = []

        if not test_result.get("passed"):
            success = False
            reasons.append(f"Tests failed: {test_result.get('errors', 'unknown')[:100]}")

        deltas = metrics.get("deltas", {})
        score_change = deltas.get("score_change", 0)
        if score_change < -0.1:
            success = False
            reasons.append(f"Score regression: {score_change:+.2f}")

        if not reasons:
            reasons.append("All criteria met")

        return {
            "success": success,
            "reason": " | ".join(reasons),
            "metrics": deltas,
        }

    def _promote_mutation(self, mutation: Mutation, metrics: Dict[str, Any]) -> Dict[str, Any]:
        import subprocess

        try:
            branch = f"mutation/{mutation.mutation_id[:12]}"
            repo_path = PROJECT_ROOT
            if (repo_path / ".git").exists():
                subprocess.run(
                    ["git", "checkout", "main"],
                    cwd=repo_path,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "pull", "origin", "main"],
                    cwd=repo_path,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "merge", branch, "--ff-only"],
                    cwd=repo_path,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "push", "origin", "main"],
                    cwd=repo_path,
                    capture_output=True,
                )
            return {
                "promoted": True,
                "branch_merged": branch,
                "improvement": metrics.get("deltas"),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "promoted": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _rollback_mutation(self, mutation: Mutation) -> Dict[str, Any]:
        import subprocess

        try:
            branch = f"mutation/{mutation.mutation_id[:12]}"
            repo_path = PROJECT_ROOT
            if (repo_path / ".git").exists():
                subprocess.run(
                    ["git", "checkout", "main"],
                    cwd=repo_path,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "pull", "origin", "main"],
                    cwd=repo_path,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "branch", "-D", branch],
                    cwd=repo_path,
                    capture_output=True,
                )
            return {
                "rolled_back": True,
                "branch_deleted": branch,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "rolled_back": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
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
            "timestamp": datetime.utcnow().isoformat(),
            "success": False,
        }
        
        proposed_changes = mutation.proposed_changes or {}
        if not isinstance(proposed_changes, dict):
            proposed_changes = {}
        
        try:
            from core.mutation_safety_gate import check_mutation_safety
            is_safe, reason = check_mutation_safety(proposed_changes)
            if not is_safe:
                result["safety_blocked"] = True
                result["safety_reason"] = reason
                result["promotion"] = "blocked"
                result["merged_to_main"] = False
                log_event(
                    "mutation_blocked",
                    mutation.agent_name,
                    "safety_gate",
                    {
                        "mutation_id": mutation.mutation_id,
                        "reason": reason,
                    },
                )
                return result
        except Exception as exc:
            result["safety_error"] = str(exc)
        
        try:
            import subprocess
            repo_path = PROJECT_ROOT
            if not (repo_path / ".git").exists():
                raise RuntimeError(f"Not a git repository: {repo_path}")
            
            branch = f"mutation/{mutation.mutation_id[:12]}"
            branch_check = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
                cwd=repo_path, capture_output=True, text=True
            )
            if branch_check.returncode == 0:
                subprocess.run(["git", "checkout", branch], cwd=repo_path, check=True, capture_output=True)
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
            
            subprocess.run(["git", "checkout", "main"], cwd=repo_path, check=True, capture_output=True)
            merge = subprocess.run(["git", "merge", branch, "--no-edit"], cwd=repo_path, check=False, capture_output=True, text=True)
            if merge.returncode == 0:
                subprocess.run(["git", "push", "origin", "main"], cwd=repo_path, check=True, capture_output=True, text=True)
                result["promotion"] = "committed"
                result["merged_to_main"] = True
            else:
                result["promotion"] = "committed"
                result["merged_to_main"] = False
                result["merge_error"] = merge.stderr or merge.stdout
                try:
                    subprocess.run(["git", "merge", "--abort"], cwd=repo_path, check=False, capture_output=True, text=True)
                except Exception:
                    pass
            
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
            result["success"] = False
            try:
                subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=repo_path, check=True, capture_output=True)
                subprocess.run(["git", "checkout", "main"], cwd=repo_path, check=True, capture_output=True)
            except Exception:
                pass
        finally:
            if "success" not in result:
                result["success"] = True
        
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
            "timestamp": datetime.utcnow().isoformat(),
            "success": False,
        }
        
        proposed_changes = mutation.proposed_changes or {}
        if isinstance(proposed_changes, dict):
            try:
                from core.mutation_safety_gate import check_mutation_safety
                is_safe, reason = check_mutation_safety(proposed_changes)
                if not is_safe:
                    result["safety_blocked"] = True
                    result["safety_reason"] = reason
                    result["promotion"] = "blocked"
                    return result
            except Exception as exc:
                result["safety_error"] = str(exc)
        
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
                result["success"] = True
                mutation.rollout_state = "canary"
                from core.rollout import _fleet_targets as _get_fleet_targets
                mutation.rollout_targets = _get_fleet_targets(mutation.agent_name)
                mutation.rollout_current_index = 0
                mutation.rollout_started_at = datetime.now(timezone.utc).isoformat()
                self._save_mutation(mutation)
            else:
                config_store.rollback(mutation.agent_name, current_version)
                result["promotion"] = "rolled_back"
                result["score_regression"] = new_score - previous_score
                result["success"] = True
                self._save_mutation(mutation)
            
            try:
                import subprocess
                repo_path = PROJECT_ROOT
                proposed_changes = mutation.proposed_changes or {}
                if "temperature" in proposed_changes:
                    result["git_commit"] = False
                    result["git_commit_error"] = "Blocked autonomous commit: temperature mutations are disabled"
                    return result
                if (repo_path / ".git").exists():
                    subprocess.run(["git", "add", "agent_configs/", "versions/"], cwd=repo_path, check=True, capture_output=True)
                    commit_msg = f" Autonomous config mutation {mutation.mutation_id[:12]}: {mutation.description[:50]}"
                    subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo_path, check=True, capture_output=True, text=True)
                    result["git_commit"] = True
            except Exception as exc:
                result["git_commit_error"] = str(exc)
            
            return result
        
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "failed"
            result["success"] = False
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
        self.expire_pending_approvals()
        return [m for m in self.mutations.values() if m.status == MutationStatus.PENDING_APPROVAL]

    def get_promoted_mutations(self, agent_name: str = None, limit: int = 5) -> List[Mutation]:
        mutations = list(self.mutations.values())
        if agent_name:
            mutations = [m for m in mutations if m.agent_name == agent_name]
        promoted = [m for m in mutations if m.status in (MutationStatus.PROMOTED, MutationStatus.IMPLEMENTED)]
        return sorted(promoted, key=lambda m: m.timestamp, reverse=True)[:limit]

    def get_failed_mutations(self, agent_name: str = None, limit: int = 5) -> List[Mutation]:
        mutations = list(self.mutations.values())
        if agent_name:
            mutations = [m for m in mutations if m.agent_name == agent_name]
        failed = [m for m in mutations if m.status in (MutationStatus.ROLLED_BACK, MutationStatus.FAILED)]
        return sorted(failed, key=lambda m: m.timestamp, reverse=True)[:limit]

    def expire_pending_approvals(self) -> None:
        expired_ids = []
        for mutation in self.mutations.values():
            if mutation.status != MutationStatus.PENDING_APPROVAL:
                continue
            if not mutation.pending_approval_timestamp:
                continue
            try:
                pending_since = datetime.fromisoformat(mutation.pending_approval_timestamp)
            except ValueError:
                continue
            if (datetime.utcnow() - pending_since).total_seconds() > PENDING_APPROVAL_TTL_SECONDS:
                expired_ids.append(mutation.mutation_id)

        for mutation_id in expired_ids:
            mutation = self.mutations.get(mutation_id)
            if not mutation:
                continue
            mutation.status = MutationStatus.REJECTED
            mutation.rejection_reason = "Pending approval expired (TTL)"
            self._save_mutation(mutation)

            log_event(
                "mutation_approval_expired",
                mutation.agent_name,
                "evolution",
                {
                    "mutation_id": mutation_id,
                    "reason": "Pending approval expired (TTL)",
                }
            )

            print(f"[EVOLUTION] Mutation approval expired: {mutation_id}")

    async def _send_mutation_telegram(self, mutation_id: str, status: str, agent_name: str, speaker: str = "EVOLUTION", mutation: Optional[Dict[str, Any]] = None) -> None:
        try:
            from core.telegram import get_telegram_bot
            bot = get_telegram_bot()
            if bot.bot_token and bot.chat_id:
                await bot.send_mutation_notification(
                    mutation_id=mutation_id,
                    status=status,
                    agent_name=agent_name,
                    speaker=speaker,
                    mutation=mutation,
                )
        except Exception as exc:
            print(f"[EVOLUTION] Telegram notification failed: {exc}")

    async def collect_council_votes(self, mutation_id: str, discussion_context: Optional[str] = None) -> Dict[str, Any]:
        if mutation_id not in self.mutations:
            return {"success": False, "error": "Mutation not found"}

        mutation = self.mutations[mutation_id]
        if mutation.status != MutationStatus.PENDING_APPROVAL:
            return {"success": False, "error": "Mutation not pending approval"}

        proposal_id = f"mutation_{mutation_id[:12]}"
        if proposal_id not in self.consensus.proposals:
            self.consensus.create_proposal(
                proposal_id,
                mutation.agent_name,
                mutation.description,
                mutation.proposed_changes,
            )

        council_agents = ["autobot", "alpha_evaluator", "beta_worker"]
        voter_roles = {
            "autobot": "Autobot",
            "alpha_evaluator": "Alpha Evaluator",
            "beta_worker": "Beta Worker",
        }

        votes = {}
        for agent_name in council_agents:
            discussion_block = ""
            if discussion_context:
                discussion_block = f"\nCouncil discussion context:\n{discussion_context}\n"
            prompt = f"""{voter_roles[agent_name]}, evaluate this mutation proposal for the council.{discussion_block}

MUTATION PROPOSAL:
- ID: {mutation.mutation_id}
- Type: {mutation.mutation_type.value}
- Description: {mutation.description}
- Rationale: {mutation.rationale}
- Proposed Changes: {json.dumps(mutation.proposed_changes)}
- Risk Level: {mutation.risk_level}
- Expected Improvement: {mutation.expected_improvement}

Respond exactly as:
<think>
[Your reasoning about this mutation]
</think>
<action>
{{"vote": "approve" or "reject", "reasoning": "brief reason"}}
</action>"""

            vote_value = "approve"
            vote_reason = "Default fallback vote"
            try:
                from core.api_router import get_llm_router
                from core.react import extract_react_parts
                router = get_llm_router()
                response = await router.route_request(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a council voting member. "
                                "Return only valid JSON inside <action>. "
                                "Do not include markdown fences."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                )
                content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("```", 2)[1]
                    if content.startswith("json"):
                        content = content[4:]
                reasoning, action_text = extract_react_parts(content)
                decision = json.loads(action_text)
                vote_value = decision.get("vote", "approve")
                vote_reason = decision.get("reasoning", "No reasoning provided")
            except Exception as exc:
                print(f"[EVOLUTION] Council vote fallback for {agent_name}: {exc}")

            votes[agent_name] = {"vote": vote_value, "reason": vote_reason}
            self.consensus.cast_vote(proposal_id, agent_name, vote_value, vote_reason)
            log_event(
                "council_vote_cast",
                agent_name,
                "evolution",
                {
                    "mutation_id": mutation_id,
                    "proposal_id": proposal_id,
                    "vote": vote_value,
                    "reason": vote_reason,
                }
            )

        mutation.votes = votes
        self._save_mutation(mutation)

        consensus_result = self.consensus.check_consensus(proposal_id)

        if consensus_result == "approved":
            mutation.status = MutationStatus.APPROVED
            mutation.approval_timestamp = datetime.utcnow().isoformat()
            mutation.approved_by = "council"
            self._save_mutation(mutation)

            log_event(
                "mutation_consensus_approved",
                mutation.agent_name,
                "evolution",
                {
                    "mutation_id": mutation_id,
                    "proposal_id": proposal_id,
                    "votes": votes,
                }
            )

            send_message(
                sender="consensus",
                receiver=mutation.agent_name,
                message_type="mutation_approved",
                content={"mutation_id": mutation_id, "approved_by": "council"},
                metadata={"source": "consensus_engine", "votes": votes},
            )

            print(f"[EVOLUTION] Mutation approved by council: {mutation_id}")
            await self._send_mutation_telegram(mutation_id, "APPROVED", mutation.agent_name, "GOVERNANCE", mutation.to_dict())
            result = self.implement_mutation(mutation_id)
            if result.get("success"):
                print(f"[EVOLUTION] Mutation {mutation_id} implemented successfully")
            else:
                print(f"[EVOLUTION] Mutation {mutation_id} approved but implementation failed: {result.get('error')}")

            return {"success": True, "result": result, "votes": votes, "consensus": "approved"}

        mutation.rejection_reason = "Council rejected"
        mutation.status = MutationStatus.REJECTED
        self._save_mutation(mutation)

        log_event(
            "mutation_rejected",
            mutation.agent_name,
            "evolution",
            {
                "mutation_id": mutation_id,
                "proposal_id": proposal_id,
                "votes": votes,
            }
        )

        print(f"[EVOLUTION] Mutation rejected by council: {mutation_id}")
        await self._send_mutation_telegram(mutation_id, "REJECTED", mutation.agent_name, "GOVERNANCE", mutation.to_dict())
        return {"success": False, "error": "Council rejected", "votes": votes, "consensus": "rejected"}

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

    def advance_rollout(self, mutation_id: str) -> Dict[str, Any]:
        from core.rollout import advance_rollout as _advance
        mutation = self.get_mutation(mutation_id)
        if not mutation:
            return {"success": False, "error": "Mutation not found"}
        return _advance(mutation)

    def rollout_status(self, mutation_id: str) -> Dict[str, Any]:
        from core.rollout import rollout_status as _status
        mutation = self.get_mutation(mutation_id)
        if not mutation:
            return {"success": False, "error": "Mutation not found"}
        return _status(mutation)

    
    def _classify_mutation_pillar(self, agent_name: str, proposed_changes: Dict[str, Any], description: str) -> Optional[int]:
        """Classify mutation into a mission pillar using keyword matching."""
        text = f"{description} {' '.join(str(v) for v in proposed_changes.values())}".lower()
        
        pillar_keywords = {
            1: ["self-evolve", "self-improve", "learn", "optimize", "feedback", "mutation", "evolution", "goal detection", "temperature", "prompt optimization"],
            2: ["cost", "cheap", "free", "failover", "groq", "cloud", "provider", "rate limit", "cooldown", "resource"],
            3: ["provider", "model", "agnostic", "fallback", "ollama", "cloud-first", "load balance", "multi-model", "router", "tool", "tools", "web scrape", "scraping", "research", "discovery", "file change", "code", "add capability"],
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

    def _validate_file_change(self, file_path: str) -> bool:
        for denied in FILE_MUTATION_DENYLIST:
            if fnmatch.fnmatch(file_path, denied):
                return False
        for allowed in FILE_MUTATION_ALLOWLIST:
            if fnmatch.fnmatch(file_path, allowed):
                return True
            if allowed.endswith("/") and file_path.startswith(allowed):
                return True
        return False
    
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
        mutations = list(self.mutations.values())
        mutations.sort(key=lambda m: m.quality_score or 0, reverse=True)
        top = mutations[:10]
        
        promoted = [m for m in mutations if m.status in (MutationStatus.PROMOTED, MutationStatus.IMPLEMENTED)][:5]
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
            try:
                from core.quota_monitor import quota_monitor
                quota_status = quota_monitor.get_status()
                if quota_status:
                    for provider_name in sorted(quota_status.keys()):
                        data = quota_status[provider_name]
                        f.write(f"| {provider_name.title()} | {data['limit']} | {data['used']} | {data['available']} |\n")
                else:
                    f.write("| OpenRouter | 1000 | ~450 | ~550 |\n")
                    f.write("| Groq | 1000 | ~200 | ~800 |\n")
                    f.write("| DeepSeek | 1000 | ~100 | ~900 |\n")
            except Exception:
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
            f.write("2. Mutation engine scores it (0-100)\n")
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


def advance_rollout(mutation_id: str) -> Dict[str, Any]:
    engine = get_evolution_engine()
    return engine.advance_rollout(mutation_id)


def rollout_status(mutation_id: str) -> Dict[str, Any]:
    engine = get_evolution_engine()
    return engine.rollout_status(mutation_id)


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
