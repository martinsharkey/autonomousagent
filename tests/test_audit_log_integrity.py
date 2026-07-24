import pytest
import os
import json
import tempfile
import shutil
from datetime import datetime
from governance.audit_log import (
    log_event,
    log_tool_invocation,
    log_consensus_vote,
    log_state_change,
    log_code_mutation,
    read_audit_log,
    verify_log_integrity,
    _compute_entry_hash,
    _compute_hmac,
    AUDIT_LOG_DIR
)


class TestAuditLogIntegrity:
    def setup_method(self):
        if os.path.exists(AUDIT_LOG_DIR):
            shutil.rmtree(AUDIT_LOG_DIR)
        os.makedirs(AUDIT_LOG_DIR)

    def teardown_method(self):
        if os.path.exists(AUDIT_LOG_DIR):
            shutil.rmtree(AUDIT_LOG_DIR)

    def test_log_event_creates_entry_with_hash(self):
        log_event("test", "agent1", "action1", {"key": "value"})
        
        entries = read_audit_log()
        assert len(entries) == 1
        
        entry = entries[0]
        assert "entry_hash" in entry
        assert "hmac" in entry
        assert "prev_hash" in entry
        assert entry["prev_hash"] == "genesis"

    def test_log_event_creates_chain(self):
        log_event("test1", "agent1", "action1", {})
        log_event("test2", "agent1", "action2", {})
        log_event("test3", "agent1", "action3", {})
        
        entries = read_audit_log()
        assert len(entries) == 3
        
        assert entries[0]["prev_hash"] == "genesis"
        assert entries[1]["prev_hash"] == entries[0]["entry_hash"]
        assert entries[2]["prev_hash"] == entries[1]["entry_hash"]

    def test_verify_log_integrity_valid(self):
        log_event("test1", "agent1", "action1", {})
        log_event("test2", "agent1", "action2", {})
        
        result = verify_log_integrity()
        assert result["valid"] is True
        assert result["entries"] == 2
        assert len(result["errors"]) == 0

    def test_verify_log_integrity_detects_tampering(self):
        log_event("test1", "agent1", "action1", {})
        
        log_file = os.path.join(AUDIT_LOG_DIR, f"audit_{datetime.utcnow().strftime('%Y%m%d')}.log")
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        entry = json.loads(lines[0])
        entry["action"] = "tampered_action"
        
        with open(log_file, 'w') as f:
            f.write(json.dumps(entry) + "\n")
        
        result = verify_log_integrity()
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_verify_log_integrity_detects_broken_chain(self):
        log_event("test1", "agent1", "action1", {})
        log_event("test2", "agent1", "action2", {})
        
        log_file = os.path.join(AUDIT_LOG_DIR, f"audit_{datetime.utcnow().strftime('%Y%m%d')}.log")
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        entry1 = json.loads(lines[0])
        entry2 = json.loads(lines[1])
        
        entry2["prev_hash"] = "wrong_hash"
        entry2["hmac"] = _compute_hmac(entry2["entry_hash"])
        
        with open(log_file, 'w') as f:
            f.write(json.dumps(entry1) + "\n")
            f.write(json.dumps(entry2) + "\n")
        
        result = verify_log_integrity()
        assert result["valid"] is False
        assert any("Chain broken" in err for err in result["errors"])

    def test_log_tool_invocation(self):
        log_tool_invocation("agent1", "tool1", {"arg": "value"}, "result")
        
        entries = read_audit_log()
        assert len(entries) == 1
        assert entries[0]["event_type"] == "tool_invocation"
        assert entries[0]["action"] == "tool1"

    def test_log_consensus_vote(self):
        log_consensus_vote("agent1", "proposal1", "approve", "good idea")
        
        entries = read_audit_log()
        assert len(entries) == 1
        assert entries[0]["event_type"] == "consensus_vote"

    def test_log_state_change(self):
        log_state_change("agent1", {"state": "old"}, {"state": "new"})
        
        entries = read_audit_log()
        assert len(entries) == 1
        assert entries[0]["event_type"] == "state_change"

    def test_log_code_mutation(self):
        log_code_mutation("agent1", "file.py", "hash1", "hash2")
        
        entries = read_audit_log()
        assert len(entries) == 1
        assert entries[0]["event_type"] == "code_mutation"

    def test_compute_entry_hash_deterministic(self):
        data = {"key": "value", "num": 123}
        hash1 = _compute_entry_hash(data)
        hash2 = _compute_entry_hash(data)
        assert hash1 == hash2

    def test_compute_hmac_deterministic(self):
        data = "test_data"
        hmac1 = _compute_hmac(data)
        hmac2 = _compute_hmac(data)
        assert hmac1 == hmac2

    def test_compute_hmac_different_secrets(self):
        data = "test_data"
        hmac1 = _compute_hmac(data, "secret1")
        hmac2 = _compute_hmac(data, "secret2")
        assert hmac1 != hmac2
