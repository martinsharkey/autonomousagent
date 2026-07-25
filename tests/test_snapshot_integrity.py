import pytest
import os
import json
import tempfile
import shutil
from datetime import datetime
from core.snapshots import (
    capture_snapshot,
    load_snapshots,
    detect_semantic_loop,
    verify_snapshot_integrity,
    verify_snapshot_chain,
    _compute_snapshot_hash,
    _compute_hmac,
    SNAPSHOT_DIR
)
from core.state import AgentState
from langchain_core.messages import HumanMessage


class TestSnapshotIntegrity:
    def setup_method(self):
        try:
            if os.path.exists(SNAPSHOT_DIR):
                shutil.rmtree(SNAPSHOT_DIR, ignore_errors=True)
        except Exception:
            pass
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)

    def teardown_method(self):
        try:
            if os.path.exists(SNAPSHOT_DIR):
                shutil.rmtree(SNAPSHOT_DIR, ignore_errors=True)
        except Exception:
            pass

    def test_capture_snapshot_creates_hash(self):
        state = AgentState(
            messages=[HumanMessage(content="test")],
            loop_count=1,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        capture_snapshot(state, "test_node")
        
        snapshots = load_snapshots("test_node")
        assert len(snapshots) == 1
        
        snapshot = snapshots[0]
        assert "snapshot_hash" in snapshot
        assert "hmac" in snapshot
        assert "prev_hash" in snapshot

    def test_capture_snapshot_creates_chain(self):
        state = AgentState(
            messages=[HumanMessage(content="test")],
            loop_count=1,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        capture_snapshot(state, "test_node")
        
        state["loop_count"] = 2
        capture_snapshot(state, "test_node")
        
        state["loop_count"] = 3
        capture_snapshot(state, "test_node")
        
        snapshots = load_snapshots("test_node")
        assert len(snapshots) == 3
        
        snapshots_sorted = sorted(snapshots, key=lambda x: x["timestamp"])
        assert snapshots_sorted[0]["prev_hash"] == "genesis"
        assert snapshots_sorted[1]["prev_hash"] == snapshots_sorted[0]["snapshot_hash"]
        assert snapshots_sorted[2]["prev_hash"] == snapshots_sorted[1]["snapshot_hash"]

    def test_verify_snapshot_integrity_valid(self):
        state = AgentState(
            messages=[HumanMessage(content="test")],
            loop_count=1,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        capture_snapshot(state, "test_node")
        
        snapshots = load_snapshots("test_node")
        snapshot_file = os.path.join(SNAPSHOT_DIR, f"snapshot_test_node_{snapshots[0]['timestamp'].replace(':', '-')}.json")
        
        snapshot_files = [f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")]
        assert len(snapshot_files) == 1
        
        result = verify_snapshot_integrity(os.path.join(SNAPSHOT_DIR, snapshot_files[0]))
        assert result["valid"] is True

    def test_verify_snapshot_integrity_detects_tampering(self):
        state = AgentState(
            messages=[HumanMessage(content="test")],
            loop_count=1,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        capture_snapshot(state, "test_node")
        
        snapshot_files = [f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")]
        snapshot_file = os.path.join(SNAPSHOT_DIR, snapshot_files[0])
        
        with open(snapshot_file, 'r') as f:
            snapshot = json.load(f)
        
        snapshot["loop_count"] = 999
        
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot, f)
        
        result = verify_snapshot_integrity(snapshot_file)
        assert result["valid"] is False

    def test_verify_snapshot_chain_valid(self):
        state = AgentState(
            messages=[HumanMessage(content="test")],
            loop_count=1,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        capture_snapshot(state, "test_node")
        
        state["loop_count"] = 2
        capture_snapshot(state, "test_node")
        
        result = verify_snapshot_chain("test_node")
        assert result["valid"] is True
        assert result["snapshots"] == 2

    def test_verify_snapshot_chain_detects_broken_chain(self):
        state = AgentState(
            messages=[HumanMessage(content="test")],
            loop_count=1,
            recent_tool_invocations=[],
            completed_nodes=[],
            codebase_hash=""
        )
        
        capture_snapshot(state, "test_node")
        
        state["loop_count"] = 2
        capture_snapshot(state, "test_node")
        
        snapshot_files = sorted([f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")])
        snapshot_file = os.path.join(SNAPSHOT_DIR, snapshot_files[1])
        
        with open(snapshot_file, 'r') as f:
            snapshot = json.load(f)
        
        snapshot["prev_hash"] = "wrong_hash"
        
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot, f)
        
        result = verify_snapshot_chain("test_node")
        assert result["valid"] is False
        assert any("Chain broken" in err for err in result["errors"])

    def test_compute_snapshot_hash_deterministic(self):
        data = {"key": "value", "num": 123}
        hash1 = _compute_snapshot_hash(data)
        hash2 = _compute_snapshot_hash(data)
        assert hash1 == hash2

    def test_compute_hmac_deterministic(self):
        data = "test_data"
        hmac1 = _compute_hmac(data)
        hmac2 = _compute_hmac(data)
        assert hmac1 == hmac2
