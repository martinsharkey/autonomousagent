"""
Phase B Demo: Self-Deployment Spider-Web Grid

Demonstrates:
1. Packaging a component as a microservice
2. Deploying to HF Spaces / Replit
3. Mesh communication setup
4. Node monitoring

Run: python demo_phase_b_deployment.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def demo_packager():
    """Demonstrate component packaging."""
    print("\n" + "=" * 60)
    print("PHASE B DEMO: Deployment Packager")
    print("=" * 60)
    
    from core.deployer import ComponentSpec, DeploymentPackager, DeploymentManager
    
    # Define a component
    spec = ComponentSpec(
        name="sentiment_analyzer",
        description="Analyzes sentiment of text using cloud LLM",
        entry_point="deploy.components.sentiment_analyzer.component.analyze_sentiment",
        requirements=["transformers", "torch"],
        platform="huggingface_spaces",
        timeout_seconds=30,
        memory_mb=512
    )
    
    # Package it
    packager = DeploymentPackager()
    component_dir = packager.package(spec)
    
    print(f"\n[OK] Packaged component: {spec.name}")
    print(f"     Platform: {spec.platform}")
    print(f"     Output: {component_dir}")
    
    # Show generated files
    print(f"\n     Generated files:")
    for f in sorted(component_dir.rglob("*")):
        if f.is_file():
            print(f"       - {f.relative_to(component_dir)}")
    
    # Deploy via manager
    manager = DeploymentManager()
    deployment = manager.deploy(spec)
    
    print(f"\n[OK] Deployment record created:")
    print(f"     Component: {deployment['component']}")
    print(f"     Platform: {deployment['platform']}")
    print(f"     Node ID: {deployment['node_id']}")
    print(f"     Status: {deployment['status']}")
    
    return spec, deployment


def demo_hf_spaces(spec):
    """Demonstrate HF Spaces deployment."""
    print("\n" + "=" * 60)
    print("PHASE B DEMO: HuggingFace Spaces Deployer")
    print("=" * 60)
    
    from deploy.hf_spaces_deployer import HuggingFaceSpacesDeployer
    
    deployer = HuggingFaceSpacesDeployer()
    deployment = deployer.deploy(spec)
    
    print(f"\n[OK] HF Space packaged:")
    print(f"     Space name: {deployment['space_name']}")
    print(f"     URL: {deployment['space_url']}")
    print(f"     Status: {deployment['status']}")
    
    return deployment


def demo_replit(spec):
    """Demonstrate Replit deployment."""
    print("\n" + "=" * 60)
    print("PHASE B DEMO: Replit Deployer")
    print("=" * 60)
    
    from deploy.replit_deployer import ReplitDeployer
    
    deployer = ReplitDeployer()
    deployment = deployer.deploy(spec)
    
    print(f"\n[OK] Replit Repl packaged:")
    print(f"     Repl name: {deployment['repl_name']}")
    print(f"     Status: {deployment['status']}")
    
    return deployment


async def demo_mesh():
    """Demonstrate mesh communication."""
    print("\n" + "=" * 60)
    print("PHASE B DEMO: Mesh Communication")
    print("=" * 60)
    
    from core.mesh_communication import MeshCommunication, MeshNode, NodeStatus
    
    mesh = MeshCommunication(council_callback_url="http://localhost:8000/api/mesh/result")
    
    # Register nodes
    nodes = [
        MeshNode(
            node_id="hf-sentiment-001",
            component="sentiment_analyzer",
            platform="huggingface_spaces",
            url="https://huggingface.co/spaces/sentiment-analyzer-council",
            status=NodeStatus.HEALTHY
        ),
        MeshNode(
            node_id="replit-sentiment-002",
            component="sentiment_analyzer",
            platform="replit",
            url="https://replit.com/user/sentiment-analyzer-council",
            status=NodeStatus.HEALTHY
        ),
    ]
    
    for node in nodes:
        result = await mesh.register_node(node)
        print(f"\n[OK] Registered node: {node.node_id}")
        print(f"     Component: {node.component}")
        print(f"     Platform: {node.platform}")
    
    # Get mesh status
    status = mesh.get_mesh_status()
    print(f"\n[OK] Mesh status:")
    print(f"     Total nodes: {status['total_nodes']}")
    print(f"     Healthy nodes: {status['healthy_nodes']}")
    
    # Broadcast a task (will fail since services aren't actually running, but shows the flow)
    print(f"\n[INFO] Broadcasting test task...")
    results = await mesh.broadcast_task({"text": "This is great!"})
    print(f"     Results: {len(results)} nodes responded")
    
    await mesh.close()
    return mesh


async def demo_monitor():
    """Demonstrate node monitoring."""
    print("\n" + "=" * 60)
    print("PHASE B DEMO: Node Monitor")
    print("=" * 60)
    
    from core.mesh_communication import MeshCommunication, MeshNode, NodeStatus
    from core.node_monitor import NodeMonitor, MonitorConfig, SpawnStrategy
    
    mesh = MeshCommunication()
    
    # Register a node
    node = MeshNode(
        node_id="test-node-001",
        component="sentiment_analyzer",
        platform="huggingface_spaces",
        url="http://localhost:8000",
        status=NodeStatus.HEALTHY
    )
    await mesh.register_node(node)
    
    # Start monitor
    config = MonitorConfig(
        health_check_interval_seconds=5,
        failure_threshold=2,
        spawn_strategy=SpawnStrategy.ROTATE_PLATFORM
    )
    monitor = NodeMonitor(mesh, config)
    
    print(f"\n[OK] Node monitor configured:")
    print(f"     Health check interval: {config.health_check_interval_seconds}s")
    print(f"     Failure threshold: {config.failure_threshold}")
    print(f"     Spawn strategy: {config.spawn_strategy.value}")
    
    status = monitor.get_mesh_status()
    print(f"\n[OK] Monitor status:")
    print(f"     Monitoring: {status['monitoring']}")
    print(f"     Total nodes: {status['mesh']['total_nodes']}")
    print(f"     Healthy nodes: {status['mesh']['healthy_nodes']}")
    
    await mesh.close()
    return monitor


def main():
    """Run all Phase B demos."""
    print("\n" + "#" * 60)
    print("# PHASE B: SELF-DEPLOYMENT DEMO")
    print("# Spider-Web Grid Architecture")
    print("#" * 60)
    
    # Demo 1: Packager
    spec, deployment = demo_packager()
    
    # Demo 2: HF Spaces
    hf_deployment = demo_hf_spaces(spec)
    
    # Demo 3: Replit
    replit_deployment = demo_replit(spec)
    
    # Demo 4: Mesh Communication
    mesh = asyncio.run(demo_mesh())
    
    # Demo 5: Node Monitor
    monitor = asyncio.run(demo_monitor())
    
    # Summary
    print("\n" + "=" * 60)
    print("PHASE B DEMO COMPLETE")
    print("=" * 60)
    print(f"\nComponents packaged: 1")
    print(f"Platforms supported: HF Spaces, Replit, Railway")
    print(f"Mesh nodes registered: {mesh.get_mesh_status()['total_nodes']}")
    print(f"Monitor configured: Yes")
    print(f"\nNext: Deploy to actual platforms with API keys")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
