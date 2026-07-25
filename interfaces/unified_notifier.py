import asyncio
from typing import Dict, Optional
from datetime import datetime
from core.operator_interface import OperatorInterface
from governance.decision_logger import DecisionLogger

class UnifiedNotifier:
    """Unified notifier that sends to both Telegram and VS Code chat"""
    
    def __init__(self):
        self.telegram = OperatorInterface()
        self.decision_logger = DecisionLogger()
    
    async def notify_mutation_decision(self, mutation_id: str, proposal: Dict, 
                                      votes: Dict[str, bool]):
        """Send mutation decision to both Telegram and VS Code chat"""
        
        decision = "APPROVED" if all(votes.values()) else "REJECTED"
        
        telegram_task = asyncio.create_task(
            self._send_telegram_notification(mutation_id, proposal, votes, decision)
        )
        
        chat_task = asyncio.create_task(
            self._send_chat_notification(mutation_id, proposal, votes, decision)
        )
        
        await asyncio.gather(telegram_task, chat_task)
        
        decision_task = asyncio.create_task(self._wait_for_telegram_response(mutation_id))
        chat_task = asyncio.create_task(self._wait_for_chat_response(mutation_id))
        
        done, pending = await asyncio.wait(
            [decision_task, chat_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        for task in pending:
            task.cancel()
        
        response = done.pop().result()
        
        interface_used = "telegram" if decision_task.done() else "chat"
        
        self.decision_logger.log(
            decision_type="OPERATOR_RESPONSE",
            metadata={
                "mutation_id": mutation_id,
                "decision": response,
                "via_interface": interface_used,
                "timestamp": datetime.now().isoformat()
            },
            mutation_id=mutation_id,
            operator_override=response
        )
        
        return response
    
    async def _send_telegram_notification(self, mutation_id: str, proposal: Dict, 
                                         votes: Dict[str, bool], decision: str):
        """Send notification via Telegram"""
        try:
            await self.telegram.request_mutation_approval(mutation_id, proposal)
            print(f"[UNIFIED] Sent Telegram notification for {mutation_id}")
        except Exception as e:
            print(f"[UNIFIED] Telegram notification failed: {e}")
    
    async def _send_chat_notification(self, mutation_id: str, proposal: Dict, 
                                     votes: Dict[str, bool], decision: str):
        """Send notification via VS Code chat"""
        message = f"""
## {decision}: {proposal.get('type', 'unknown')}

**Mutation ID**: {mutation_id}

**Mission Alignment**: {proposal.get('mission_rationale', 'N/A')[:200]}

**Council Votes**:
- Autobot: {'✅' if votes.get('autobot') else '❌'}
- Alpha: {'✅' if votes.get('alpha_evaluator') else '❌'}
- Beta: {'✅' if votes.get('beta_worker') else '❌'}

**Decision**: {decision}

---

Respond with: `approve`, `hold`, or `reject`
"""
        print(f"[UNIFIED] Sent chat notification for {mutation_id}")
        print(message)
    
    async def _wait_for_telegram_response(self, mutation_id: str, timeout: int = 3600) -> str:
        """Wait for response from Telegram"""
        await asyncio.sleep(timeout)
        return "TIMEOUT"
    
    async def _wait_for_chat_response(self, mutation_id: str, timeout: int = 3600) -> str:
        """Wait for response from VS Code chat"""
        await asyncio.sleep(timeout)
        return "TIMEOUT"
    
    async def notify_rollback_decision(self, mutation_id: str, current_version: str,
                                      target_version: str, risk_assessment: Dict):
        """Send rollback decision to both interfaces"""
        
        telegram_task = asyncio.create_task(
            self.telegram.request_rollback_approval(
                mutation_id, current_version, target_version, risk_assessment
            )
        )
        
        chat_task = asyncio.create_task(
            self._send_rollback_chat_notification(
                mutation_id, current_version, target_version, risk_assessment
            )
        )
        
        await asyncio.gather(telegram_task, chat_task)
    
    async def _send_rollback_chat_notification(self, mutation_id: str, current_version: str,
                                              target_version: str, risk_assessment: Dict):
        """Send rollback notification via chat"""
        message = f"""
## 🔴 ROLLBACK REQUIRED

**Current Version**: {current_version}
**Target Version**: {target_version}
**Mutation ID**: {mutation_id}

**Risk Assessment**:
- Data Loss Risk: {risk_assessment.get('data_loss_risk', 'UNKNOWN')}
- Fields Lost: {', '.join(risk_assessment.get('fields_lost', []))}
- Compatibility Issues: {len(risk_assessment.get('compatibility_issues', []))}

---

Respond with: `approve` or `reject`
"""
        print(f"[UNIFIED] Sent rollback chat notification for {mutation_id}")
        print(message)
    
    async def notify_operator(self, message: str):
        """Send a general notification to operator via both interfaces"""
        telegram_task = asyncio.create_task(self.telegram.notify_operator(message))
        chat_task = asyncio.create_task(self._send_chat_message(message))
        
        await asyncio.gather(telegram_task, chat_task)
    
    async def _send_chat_message(self, message: str):
        """Send message via chat"""
        print(f"[UNIFIED] Chat notification: {message}")
