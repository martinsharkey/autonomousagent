import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
from governance.decision_logger import DecisionLogger
from interfaces.unified_notifier import UnifiedNotifier

class EscalationSeverity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class EscalationHandler:
    def __init__(self):
        self.decision_logger = DecisionLogger()
        self.notifier = UnifiedNotifier()
        self.active_escalations: Dict[str, Dict] = {}
    
    async def check_escalation_conditions(self, state: Dict) -> Optional[str]:
        """Check if any escalation conditions are met"""
        
        if state.get("requires_operator_approval"):
            return await self._escalate_operator_approval(state)
        
        if state.get("escalation_reason"):
            return await self._escalate_to_operator(
                state["escalation_reason"], 
                EscalationSeverity.MEDIUM,
                state.get("active_mutation_id")
            )
        
        if self._is_deadlocked(state):
            return await self._escalate_deadlock(state)
        
        if self._is_regression_detected(state):
            return await self._escalate_regression(state)
        
        if self._is_security_alert(state):
            return await self._escalate_security_alert(state)
        
        return None
    
    async def _escalate_operator_approval(self, state: Dict) -> str:
        """Escalate for operator approval"""
        mutation_id = state.get("active_mutation_id")
        reason = state.get("escalation_reason", "Operator approval required")
        
        message = f"""
⚠️ OPERATOR APPROVAL REQUIRED

Mutation ID: {mutation_id}
Reason: {reason}

Council votes: {state.get('council_votes', {})}
Mission scores: {state.get('mission_scores', {})}

Please review and approve/reject.
"""
        
        await self.notifier.notify_operator(message)
        
        self.decision_logger.log(
            decision_type="ESCALATION_OPERATOR_APPROVAL",
            metadata={
                "mutation_id": mutation_id,
                "reason": reason,
                "votes": state.get("council_votes")
            },
            mutation_id=mutation_id
        )
        
        return "ESCALATED_FOR_APPROVAL"
    
    async def _escalate_deadlock(self, state: Dict) -> str:
        """Escalate voting deadlock"""
        mutation_id = state.get("active_mutation_id")
        votes = state.get("council_votes", {})
        
        message = f"""
⚠️ VOTING DEADLOCK

Mutation ID: {mutation_id}
Time deadlocked: 30 min
Council votes: {votes}

What should I do?
[ REQUEST MORE TIME ] [ ESCALATE TO VOTING MODEL AGAIN ] [ MANUAL REVIEW NEEDED ]
"""
        
        await self.notifier.notify_operator(message)
        
        self.decision_logger.log(
            decision_type="DEADLOCK_ESCALATION",
            metadata={
                "mutation_id": mutation_id,
                "votes": votes,
                "deadlock_duration_min": 30
            },
            mutation_id=mutation_id
        )
        
        return "DEADLOCK_ESCALATED"
    
    async def _escalate_regression(self, state: Dict) -> str:
        """Escalate regression detection"""
        mutation_id = state.get("active_mutation_id")
        
        message = f"""
🔴 REGRESSION DETECTED

Mutation ID: {mutation_id}
Error rate increased significantly post-promotion

Rollback assessment: PENDING
Target version: {state.get('rollback_target_version', 'unknown')}

Approve rollback?
[ YES - ROLLBACK NOW ] [ HOLD ] [ INVESTIGATE FIRST ]
"""
        
        await self.notifier.notify_operator(message)
        
        self.decision_logger.log(
            decision_type="REGRESSION_ESCALATION",
            metadata={
                "mutation_id": mutation_id,
                "target_version": state.get("rollback_target_version")
            },
            mutation_id=mutation_id
        )
        
        return "REGRESSION_ESCALATED"
    
    async def _escalate_security_alert(self, state: Dict) -> str:
        """Escalate security alert"""
        mutation_id = state.get("active_mutation_id")
        
        message = f"""
🚨 SECURITY ALERT

Mutation ID: {mutation_id}
Prompt injection or malicious pattern detected

BLOCKED immediately. Manual review required.

[ REVIEW ] [ OVERRIDE BLOCK ] [ REJECT MUTATION ]
"""
        
        await self.notifier.notify_operator(message)
        
        self.decision_logger.log(
            decision_type="SECURITY_ALERT_ESCALATION",
            metadata={
                "mutation_id": mutation_id,
                "action": "BLOCKED"
            },
            mutation_id=mutation_id
        )
        
        return "SECURITY_BLOCKED"
    
    async def _escalate_to_operator(self, reason: str, severity: EscalationSeverity,
                                   mutation_id: str = None) -> str:
        """General escalation to operator"""
        message = f"""
⚠️ ESCALATION ({severity.value})

Reason: {reason}
Mutation ID: {mutation_id or 'N/A'}

Please review and provide guidance.
"""
        
        await self.notifier.notify_operator(message)
        
        self.decision_logger.log(
            decision_type="GENERAL_ESCALATION",
            metadata={
                "reason": reason,
                "severity": severity.value,
                "mutation_id": mutation_id
            },
            mutation_id=mutation_id
        )
        
        return f"ESCALATED_{severity.value}"
    
    def _is_deadlocked(self, state: Dict) -> bool:
        """Check if voting is deadlocked"""
        votes = state.get("council_votes", {})
        if not votes:
            return False
        
        vote_values = list(votes.values())
        if None in vote_values:
            return False
        
        return not all(v == vote_values[0] for v in vote_values)
    
    def _is_regression_detected(self, state: Dict) -> bool:
        """Check if regression is detected"""
        return state.get("rollback_pending", False)
    
    def _is_security_alert(self, state: Dict) -> bool:
        """Check if security alert is triggered"""
        mission_scores = state.get("mission_scores", {})
        return any(score < 0.3 for score in mission_scores.values())
