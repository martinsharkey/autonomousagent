from typing import Dict, Any
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage

JUDGE_MODELS = [
    {"model": "qwen3.5:9b", "base_url": "http://localhost:11434"},
    {"model": "qwen2.5:14b", "base_url": "http://localhost:11434"},
]

ALLOWED_ACTIONS = [
    "read_file",
    "write_file",
    "execute_code",
    "search_tools",
    "inspect_tool",
    "delegate_task"
]

BLOCKED_PATTERNS = [
    "rm -rf",
    "format",
    "delete_all",
    "shutdown",
    "sudo",
    "chmod 777",
    "curl.*|.*sh",
    "wget.*|.*sh"
]

class IntentJudge:
    def __init__(self):
        self.judges = []
        for config in JUDGE_MODELS:
            try:
                judge = ChatOllama(
                    model=config["model"],
                    temperature=0.0,
                    base_url=config["base_url"]
                )
                self.judges.append(judge)
            except Exception as e:
                print(f"[INTENT JUDGE] Failed to initialize {config['model']}: {e}")
    
    def _check_blocked_patterns(self, action: str) -> bool:
        import re
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, action, re.IGNORECASE):
                return True
        return False
    
    def _check_allowed_action(self, action: str) -> bool:
        return action in ALLOWED_ACTIONS
    
    async def judge_intent(self, agent_name: str, action: str, context: Dict[str, Any]) -> str:
        if self._check_blocked_patterns(action):
            print(f"[INTENT JUDGE] BLOCKED: Dangerous pattern detected in {action}")
            return "BLOCK"
        
        if not self._check_allowed_action(action):
            print(f"[INTENT JUDGE] BLOCKED: Unknown action {action}")
            return "BLOCK"
        
        for judge in self.judges:
            try:
                prompt = f"""You are a security judge for a multi-agent system.
Agent: {agent_name}
Proposed Action: {action}
Context: {json.dumps(context)}

Evaluate if this action is safe and aligned with the system's goals.
Respond with ONLY "ALLOW" or "BLOCK" and a brief reason.

Your decision:"""
                
                response = await judge.ainvoke([HumanMessage(content=prompt)])
                decision = response.content.strip().upper()
                
                if "ALLOW" in decision:
                    print(f"[INTENT JUDGE] ALLOWED: {action} by {agent_name}")
                    return "ALLOW"
                elif "BLOCK" in decision:
                    print(f"[INTENT JUDGE] BLOCKED: {action} by {agent_name}")
                    return "BLOCK"
            
            except Exception as e:
                print(f"[INTENT JUDGE] Judge failed, trying next: {e}")
                continue
        
        print(f"[INTENT JUDGE] All judges failed, defaulting to BLOCK for safety")
        return "BLOCK"

import json

intent_judge = IntentJudge()

async def verify_intent(agent_name: str, action: str, context: Dict[str, Any]) -> bool:
    decision = await intent_judge.judge_intent(agent_name, action, context)
    return decision == "ALLOW"
