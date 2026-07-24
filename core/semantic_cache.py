from typing import List, Dict
from core.state import AgentState
import hashlib
import json

_invocation_cache: List[str] = []
MAX_CACHE_SIZE = 10

def _generate_invocation_hash(tool_name: str, arguments: Dict) -> str:
    payload = json.dumps({"tool": tool_name, "args": arguments}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()

def check_duplicate_invocation(state: AgentState) -> bool:
    last_message = state["messages"][-1].content if state["messages"] else ""

    if "tool_call" in last_message:
        try:
            invocation_hash = hashlib.sha256(last_message.encode()).hexdigest()
            if invocation_hash in _invocation_cache:
                print(f"[SEMANTIC CACHE] Duplicate invocation detected and blocked")
                return True
            _invocation_cache.append(invocation_hash)
            if len(_invocation_cache) > MAX_CACHE_SIZE:
                _invocation_cache.pop(0)
        except Exception as e:
            print(f"[SEMANTIC CACHE] Error checking cache: {e}")

    return False

def clear_cache():
    global _invocation_cache
    _invocation_cache = []
