#!/usr/bin/env python3
"""Quick integration audit: mutation approval flow, display, and Phase B spider-web."""
import os
import sys
import json
from pathlib import Path

from dotenv import load_dotenv

os.chdir(Path(__file__).parent.parent)

load_dotenv()

from core.evolution import get_evolution_engine, propose_mutation, approve_mutation, implement_mutation, MutationType, Mutation, MutationStatus
from core.telegram import TelegramBot, format_council_message
from core.deployer import DeploymentPackager, ComponentSpec
from core.mesh_communication import MeshCommunication, MeshNode
from core.node_monitor import NodeMonitor


def test_mutation_content():
    print("[1] Mutation content test")
    engine = get_evolution_engine()
    engine.mutations.clear()
    
    m = Mutation(
        agent_name="autobot",
        mutation_type=MutationType.PARAMETER_ADJUSTMENT,
        description="Lower temperature for deterministic responses",
        rationale="Current responses are too random",
        proposed_changes={"temperature": 0.15, "max_retries": 4},
        expected_improvement=0.1,
        risk_level="medium"
    )
    m.mission_pillar = 1
    m.mission_description = "Recursive Self-Evolution"
    m.quality_score = 70
    m.quality_breakdown = {
        "alignment": 50,
        "performance_gain": 50,
        "risk_safety": 50,
        "testability": 50
    }
    m.status = MutationStatus.APPROVED
    engine.mutations[m.mutation_id] = m
    engine._save_mutation(m)
    
    assert m.description == "Lower temperature for deterministic responses"
    assert m.proposed_changes["temperature"] == 0.15
    assert m.mutation_id in engine.mutations
    print(f"    Injected mutation with content: {m.mutation_id[:12]}...")
    
    import asyncio
    notification = asyncio.run(TelegramBot().send_mutation_notification(
        mutation_id=m.mutation_id,
        status="PROPOSED",
        agent_name=m.agent_name,
        speaker="EVOLUTION",
        mutation=m.to_dict()
    ))
    print(f"    Telegram notification result: {notification}")
    
    approved = approve_mutation(m.mutation_id, approved_by="human_telegram")
    print(f"    Approval result: {approved}")
    
    result = implement_mutation(m.mutation_id)
    print(f"    Implementation result: success={result.get('success')}")
    print(f"    Implementation execution: {result.get('execution')}")
    
    assert m.to_dict()["description"]
    assert approved is True
    print("    PASSED")


def test_mutation_code_commit_path():
    print("[2] Code mutation commit path test")
    engine = get_evolution_engine()
    engine.mutations.clear()
    
    m = Mutation(
        agent_name="autobot",
        mutation_type=MutationType.BEHAVIOR_CHANGE,
        description="Add hello world marker to evolution test file",
        rationale="Testing inline code mutation path",
        proposed_changes={
            "file_changes": [
                {"path": "evolution/mutation_audit_test.txt", "kind": "add", "content": "hello world from autonomous mutation\n"}
            ],
            "commit_message": "test: add hello world marker"
        },
        expected_improvement=0.05,
        risk_level="low"
    )
    m.mission_pillar = 1
    m.mission_description = "Recursive Self-Evolution"
    m.quality_score = 70
    m.quality_breakdown = {
        "alignment": 50,
        "performance_gain": 50,
        "risk_safety": 50,
        "testability": 50
    }
    m.status = MutationStatus.APPROVED
    engine.mutations[m.mutation_id] = m
    engine._save_mutation(m)
    
    print(f"    Injected code mutation: {m.mutation_id[:12]}...")
    print(f"    Status after injection: {m.status.value}")
    
    approved = approve_mutation(m.mutation_id, approved_by="human_telegram")
    print(f"    Approval result: {approved}")
    
    result = implement_mutation(m.mutation_id)
    print(f"    Implementation result keys: {list(result.keys())}")
    print(f"    Execution type: {result.get('execution')}")
    print(f"    Changes applied: {result.get('changes_applied')}")
    
    target = Path("evolution/mutation_audit_test.txt")
    if target.exists():
        content = target.read_text(encoding="utf-8")
        print(f"    File content: {content.strip()}")
        target.unlink()
    
    assert approved is True
    print("    PASSED")


def test_spider_web_components():
    print("[3] Spider-web component integration test")
    spec = ComponentSpec(
        name="sentiment_analyzer",
        description="Simple sentiment analyzer",
        methods=[{"name": "analyze_sentiment", "params": [{"name": "text", "type": "str"}], "returns": "dict"}],
        dependencies=[],
        author="autobot"
    )
    
    packager = DeploymentPackager()
    package = packager.package_component(spec)
    assert package is not None
    print(f"    Packaged component: {package.name}")
    
    mesh = MeshCommunication()
    node = MeshNode(node_id="hf-sentiment", component="sentiment_analyzer", platform="hf_spaces", url="https://test.hf.space")
    import asyncio
    asyncio.run(mesh.register_node(node))
    assert "hf-sentiment" in mesh.nodes
    print(f"    Registered node: hf-sentiment")
    
    monitor = NodeMonitor(mesh=mesh)
    status = monitor.get_mesh_status()
    assert status["total_nodes"] >= 1
    print(f"    Node monitor sees nodes: {status['total_nodes']}")
    print("    PASSED")


def test_telegram_goal_wiring():
    print("[4] Telegram goal wiring test")
    from core.goals import get_goal_store
    
    goal_store = get_goal_store()
    goal_id = goal_store.create_goal("Integration test goal", source="telegram", priority=10)
    goals = goal_store.get_pending_goals(limit=5)
    assert any(g["goal_id"] == goal_id for g in goals)
    print(f"    Created goal via goal store: {goal_id[:12]}...")
    print(f"    Pending goals: {len(goals)}")
    print("    PASSED")


def main():
    print("=" * 60)
    print("INTEGRATION AUDIT")
    print("=" * 60)
    test_mutation_content()
    print()
    test_mutation_code_commit_path()
    print()
    test_spider_web_components()
    print()
    test_telegram_goal_wiring()
    print()
    print("=" * 60)
    print("ALL INTEGRATION AUDITS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
