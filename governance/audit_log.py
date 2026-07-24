import json
import os
from datetime import datetime
from typing import Dict, Any, List

AUDIT_LOG_DIR = "audit_logs"

def _ensure_audit_dir():
    if not os.path.exists(AUDIT_LOG_DIR):
        os.makedirs(AUDIT_LOG_DIR)

def log_event(event_type: str, agent_name: str, action: str, details: Dict[str, Any]):
    _ensure_audit_dir()
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "agent": agent_name,
        "action": action,
        "details": details
    }
    
    log_file = os.path.join(AUDIT_LOG_DIR, f"audit_{datetime.utcnow().strftime('%Y%m%d')}.log")
    
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
        f.flush()
        os.fsync(f.fileno())

def log_tool_invocation(agent_name: str, tool_name: str, arguments: Dict[str, Any], result: str):
    log_event(
        event_type="tool_invocation",
        agent_name=agent_name,
        action=tool_name,
        details={"arguments": arguments, "result": result[:500]}
    )

def log_consensus_vote(agent_name: str, proposal: str, vote: str, reason: str):
    log_event(
        event_type="consensus_vote",
        agent_name=agent_name,
        action="vote",
        details={"proposal": proposal, "vote": vote, "reason": reason}
    )

def log_state_change(agent_name: str, old_state: Dict[str, Any], new_state: Dict[str, Any]):
    log_event(
        event_type="state_change",
        agent_name=agent_name,
        action="state_transition",
        details={"old_state": old_state, "new_state": new_state}
    )

def log_code_mutation(agent_name: str, file_path: str, old_hash: str, new_hash: str):
    log_event(
        event_type="code_mutation",
        agent_name=agent_name,
        action="file_modified",
        details={"file": file_path, "old_hash": old_hash, "new_hash": new_hash}
    )

def read_audit_log(date: str = None, limit: int = 100) -> List[Dict[str, Any]]:
    _ensure_audit_dir()
    
    if date is None:
        date = datetime.utcnow().strftime('%Y%m%d')
    
    log_file = os.path.join(AUDIT_LOG_DIR, f"audit_{date}.log")
    
    if not os.path.exists(log_file):
        return []
    
    entries = []
    with open(log_file, "r") as f:
        for line in f:
            try:
                entries.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    
    return entries[-limit:]

def verify_log_integrity(date: str = None) -> bool:
    _ensure_audit_dir()
    
    if date is None:
        date = datetime.utcnow().strftime('%Y%m%d')
    
    log_file = os.path.join(AUDIT_LOG_DIR, f"audit_{date}.log")
    
    if not os.path.exists(log_file):
        return True
    
    try:
        with open(log_file, "r") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    json.loads(line.strip())
                except json.JSONDecodeError:
                    print(f"[AUDIT] Integrity check failed at line {line_num}")
                    return False
        return True
    except Exception as e:
        print(f"[AUDIT] Integrity check error: {e}")
        return False
