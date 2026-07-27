"""
Phase B: Node Monitor & Auto-Spawner

Monitors health of deployed nodes, detects failures, and automatically
spawns replacements across platforms.
"""
import os
import json
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from core.mesh_communication import MeshCommunication, MeshNode, NodeStatus
from core.deployer import ComponentSpec, DeploymentManager, DeploymentPackager
from deploy.hf_spaces_deployer import HuggingFaceSpacesDeployer
from deploy.replit_deployer import ReplitDeployer
from governance.audit_log import log_event

logger = logging.getLogger("node_monitor")


class SpawnStrategy(str, Enum):
    SAME_PLATFORM = "same_platform"
    ROTATE_PLATFORM = "rotate_platform"
    LOAD_BALANCE = "load_balance"


@dataclass
class MonitorConfig:
    """Configuration for node monitoring."""
    health_check_interval_seconds: int = 30
    failure_threshold: int = 3
    respawn_delay_seconds: int = 60
    spawn_strategy: SpawnStrategy = SpawnStrategy.ROTATE_PLATFORM
    max_nodes_per_component: int = 3
    platforms: List[str] = field(default_factory=lambda: ["huggingface_spaces", "replit", "railway"])


class NodeMonitor:
    """Monitor deployed nodes and auto-spawn replacements."""
    
    def __init__(self, mesh: MeshCommunication, config: Optional[MonitorConfig] = None):
        self.mesh = mesh
        self.config = config or MonitorConfig()
        self.deployment_manager = DeploymentManager()
        self.failure_counts: Dict[str, int] = {}
        self.last_spawn: Dict[str, datetime] = {}
        self.monitoring_task: Optional[asyncio.Task] = None
        self.running = False
    
    async def start(self):
        """Start the monitoring loop."""
        if self.running:
            return
        
        self.running = True
        self.monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info("Node monitor started")
    
    async def stop(self):
        """Stop the monitoring loop."""
        self.running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Node monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                await self._check_all_nodes()
                await asyncio.sleep(self.config.health_check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(self.config.health_check_interval_seconds)
    
    async def _check_all_nodes(self):
        """Check health of all nodes and handle failures."""
        health_results = await self.mesh.check_all_nodes_health()
        
        for node_id, health in health_results.items():
            if health["status"] == "unhealthy":
                await self._handle_node_failure(node_id, health)
            else:
                self.failure_counts.pop(node_id, 0)
    
    async def _handle_node_failure(self, node_id: str, health: Dict[str, Any]):
        """Handle a failed node."""
        self.failure_counts[node_id] = self.failure_counts.get(node_id, 0) + 1
        
        node = self.mesh.get_node(node_id)
        if not node:
            return
        
        logger.warning(f"Node {node_id} unhealthy (count={self.failure_counts[node_id]})")
        
        if self.failure_counts[node_id] >= self.config.failure_threshold:
            log_event(
                "node_failure_detected",
                "node_monitor",
                "failure",
                {
                    "node_id": node_id,
                    "component": node.component,
                    "platform": node.platform,
                    "failures": self.failure_counts[node_id]
                }
            )
            
            # Check if we should respawn
            if await self._should_respawn(node):
                await self._respawn_node(node)
    
    async def _should_respawn(self, node: MeshNode) -> bool:
        """Determine if a node should be respawned."""
        # Check cooldown
        last_spawn_time = self.last_spawn.get(node.component)
        if last_spawn_time and datetime.utcnow() - last_spawn_time < timedelta(seconds=self.config.respawn_delay_seconds):
            return False
        
        # Check max nodes
        nodes_for_component = self.mesh.get_nodes_by_component(node.component)
        if len(nodes_for_component) >= self.config.max_nodes_per_component:
            return False
        
        return True
    
    async def _respawn_node(self, failed_node: MeshNode):
        """Respawn a failed node, potentially on a different platform."""
        component = failed_node.component
        
        # Select platform based on strategy
        if self.config.spawn_strategy == SpawnStrategy.SAME_PLATFORM:
            new_platform = failed_node.platform
        elif self.config.spawn_strategy == SpawnStrategy.ROTATE_PLATFORM:
            new_platform = self._select_alternative_platform(failed_node.platform)
        else:  # LOAD_BALANCE
            new_platform = self._select_least_loaded_platform(component)
        
        logger.info(f"Respawning {component} on {new_platform}")
        
        # Create component spec
        spec = ComponentSpec(
            name=component,
            description=f"Auto-respawned {component} microservice",
            entry_point=failed_node.metadata.get("entry_point", "core.api_router.get_llm_router"),
            platform=new_platform,
            metadata={"entry_point": failed_node.metadata.get("entry_point", "")}
        )
        
        # Deploy based on platform
        if new_platform == "huggingface_spaces":
            deployer = HuggingFaceSpacesDeployer()
            deployment = deployer.deploy(spec)
        elif new_platform == "replit":
            deployer = ReplitDeployer()
            deployment = deployer.deploy(spec)
        else:
            deployment = self.deployment_manager.deploy(spec)
        
        # Register new node
        new_node = MeshNode(
            node_id=deployment["node_id"],
            component=component,
            platform=new_platform,
            url=deployment.get("space_url") or deployment.get("repl_url") or f"http://{component}:8000",
            status=NodeStatus.UNKNOWN,
            metadata={"deployment": deployment}
        )
        
        await self.mesh.register_node(new_node)
        
        self.last_spawn[component] = datetime.utcnow()
        self.failure_counts.pop(failed_node.node_id, None)
        
        log_event(
            "node_respawned",
            "node_monitor",
            "respawn",
            {
                "failed_node": failed_node.node_id,
                "new_node": new_node.node_id,
                "platform": new_platform,
                "component": component
            }
        )
    
    def _select_alternative_platform(self, current_platform: str) -> str:
        """Select a different platform for respawning."""
        available = [p for p in self.config.platforms if p != current_platform]
        return available[0] if available else current_platform
    
    def _select_least_loaded_platform(self, component: str) -> str:
        """Select the platform with the fewest nodes for load balancing."""
        platform_counts: Dict[str, int] = {}
        for node in self.mesh.nodes.values():
            if node.component == component:
                platform_counts[node.platform] = platform_counts.get(node.platform, 0) + 1
        
        if not platform_counts:
            return self.config.platforms[0]
        
        return min(platform_counts, key=platform_counts.get)
    
    def get_mesh_status(self) -> Dict[str, Any]:
        """Get overall mesh and monitor status."""
        mesh_status = self.mesh.get_mesh_status()
        
        return {
            "monitoring": self.running,
            "health_check_interval": self.config.health_check_interval_seconds,
            "failure_threshold": self.config.failure_threshold,
            "spawn_strategy": self.config.spawn_strategy.value,
            "failure_counts": dict(self.failure_counts),
            "last_spawn": {k: v.isoformat() for k, v in self.last_spawn.items()},
            "mesh": mesh_status
        }
