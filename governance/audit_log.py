import json
import os
import hashlib
import hmac
from datetime import datetime
from typing import Dict, Any, List, Optional
from governance.keys import get_audit_log_key

AUDIT_LOG_DIR = "audit_logs"

def _ensure_audit_dir():
    if not os.path.exists(AUDIT_LOG_DIR):
        os.makedirs(AUDIT_LOG_DIR)

def _compute_entry_hash(entry_data: Dict[str, Any]) -> str:
    entry_json = json.dumps(entry_data, sort_keys=True)
    return hashlib.sha256(entry_json.encode()).hexdigest()

def _compute_hmac(data: str, secret: str = None) -> str:
    if secret is None:
        secret = get_audit_log_key()
    return hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()

def _get_last_entry_hash(log_file: str) -> Optional[str]:
    if not os.path.exists(log_file):
        return None
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            if lines:
                last_entry = json.loads(lines[-1].strip())
                return last_entry.get("entry_hash")
    except Exception:
        pass
    return None

def log_event(event_type: str, agent_name: str, action: str, details: Dict[str, Any]):
    _ensure_audit_dir()
    
    log_file = os.path.join(AUDIT_LOG_DIR, f"audit_{datetime.utcnow().strftime('%Y%m%d')}.log")
    prev_hash = _get_last_entry_hash(log_file)
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "agent": agent_name,
        "action": action,
        "details": details,
        "prev_hash": prev_hash or "genesis"
    }
    
    entry_hash = _compute_entry_hash(log_entry)
    log_entry["entry_hash"] = entry_hash
    
    hmac_signature = _compute_hmac(entry_hash)
    log_entry["hmac"] = hmac_signature
    
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

def verify_log_integrity(date: str = None, secret: str = None) -> Dict[str, Any]:
    if secret is None:
        secret = get_audit_log_key()
    
    _ensure_audit_dir()
    
    if date is None:
        date = datetime.utcnow().strftime('%Y%m%d')
    
    log_file = os.path.join(AUDIT_LOG_DIR, f"audit_{date}.log")
    
    if not os.path.exists(log_file):
        return {"valid": True, "entries": 0, "errors": []}
    
    errors = []
    entries = []
    expected_prev_hash = None
    
    try:
        with open(log_file, "r") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line.strip())
                    entries.append(entry)
                    
                    if "entry_hash" not in entry:
                        errors.append(f"Line {line_num}: Missing entry_hash")
                        continue
                    
                    if "hmac" not in entry:
                        errors.append(f"Line {line_num}: Missing HMAC signature")
                        continue
                    
                    stored_hmac = entry["hmac"]
                    entry_hash = entry["entry_hash"]
                    computed_hmac = _compute_hmac(entry_hash, secret)
                    
                    if not hmac.compare_digest(stored_hmac, computed_hmac):
                        errors.append(f"Line {line_num}: HMAC verification failed")
                    
                    if expected_prev_hash is None:
                        if entry.get("prev_hash") != "genesis":
                            errors.append(f"Line {line_num}: First entry should have prev_hash='genesis'")
                    else:
                        if entry.get("prev_hash") != expected_prev_hash:
                            errors.append(f"Line {line_num}: Chain broken - prev_hash mismatch")
                    
                    expected_prev_hash = entry_hash
                    
                except json.JSONDecodeError:
                    errors.append(f"Line {line_num}: Invalid JSON")
        
        return {
            "valid": len(errors) == 0,
            "entries": len(entries),
            "errors": errors
        }
    except Exception as e:
        return {
            "valid": False,
            "entries": 0,
            "errors": [f"Read error: {str(e)}"]
        }
