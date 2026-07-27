"""
Phase B: Mesh Communication

Handles communication between the main council and deployed microservices.
Provides task distribution, result aggregation, health checks, and node registry.
"""
import os
import json
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

import httpx

from governance.audit_log import log_event

logger = logging.getLogger("mesh_communication")


class NodeStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class MeshNode:
    """Represents a deployed microservice node."""
    node_id: str
    component: str
    platform: str
    url: str
    status: NodeStatus = NodeStatus.UNKNOWN
    last_health_check: Optional[str] = None
    tasks_completed: int = 0
    quota_used_percent: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class MeshCommunication:
    """Communication layer between council and deployed nodes."""
    
    def __init__(self, council_callback_url: Optional[str] = None):
        self.council_callback_url = council_callback_url or os.getenv("COUNCIL_CALLBACK_URL", "http://localhost:8000/api/mesh/result")
        self.nodes: Dict[str, MeshNode] = {}
        self.task_results: Dict[str, Dict[str, Any]] = {}
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def register_node(self, node: MeshNode) -> Dict[str, Any]:
        """Register a new node in the mesh."""
        self.nodes[node.node_id] = node
        
        log_event(
            "node_registered",
            "mesh",
            "register",
            {
                "node_id": node.node_id,
                "component": node.component,
                "platform": node.platform,
                "url": node.url
            }
        )
        
        return {
            "status": "registered",
            "node_id": node.node_id,
            "mesh_size": len(self.nodes)
        }
    
    async def unregister_node(self, node_id: str) -> Dict[str, Any]:
        """Remove a node from the mesh."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            
            log_event(
                "node_unregistered",
                "mesh",
                "unregister",
                {"node_id": node_id}
            )
            
            return {"status": "unregistered", "node_id": node_id}
        return {"status": "not_found", "node_id": node_id}
    
    async def send_task(self, node_id: str, task_input: Dict[str, Any], 
                       task_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a task to a specific node."""
        if node_id not in self.nodes:
            return {"error": "Node not found", "node_id": node_id}
        
        node = self.nodes[node_id]
        task_id = task_id or str(uuid.uuid4())
        
        task_payload = {
            "task_id": task_id,
            "input": task_input,
            "callback_url": self.council_callback_url
        }
        
        try:
            response = await self.client.post(
                f"{node.url}/task",
                json=task_payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            
            self.task_results[task_id] = {
                "node_id": node_id,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return {
                "status": "submitted",
                "task_id": task_id,
                "node_id": node_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Failed to send task to {node_id}: {e}")
            return {"error": str(e), "task_id": task_id, "node_id": node_id}
    
    async def broadcast_task(self, task_input: Dict[str, Any], 
                            component_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Broadcast a task to all healthy nodes (or filtered nodes)."""
        results = []
        target_nodes = [
            node for node in self.nodes.values()
            if node.status == NodeStatus.HEALTHY
            and (component_filter is None or node.component == component_filter)
        ]
        
        for node in target_nodes:
            result = await self.send_task(node.node_id, task_input)
            results.append(result)
        
        return results
    
    async def check_node_health(self, node_id: str) -> Dict[str, Any]:
        """Check health of a specific node."""
        if node_id not in self.nodes:
            return {"status": "not_found", "node_id": node_id}
        
        node = self.nodes[node_id]
        
        try:
            response = await self.client.get(f"{node.url}/health", timeout=10.0)
            response.raise_for_status()
            health_data = response.json()
            
            node.status = NodeStatus.HEALTHY
            node.last_health_check = datetime.utcnow().isoformat()
            node.tasks_completed = health_data.get("tasks_completed", node.tasks_completed)
            node.quota_used_percent = health_data.get("quota_used_percent", 0.0)
            node.metadata.update(health_data)
            
            return {
                "node_id": node_id,
                "status": "healthy",
                "data": health_data
            }
            
        except Exception as e:
            node.status = NodeStatus.UNHEALTHY
            node.last_health_check = datetime.utcnow().isoformat()
            
            return {
                "node_id": node_id,
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_all_nodes_health(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all registered nodes."""
        results = {}
        for node_id in self.nodes:
            results[node_id] = await self.check_node_health(node_id)
        return results
    
    def get_node(self, node_id: str) -> Optional[MeshNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)
    
    def get_nodes_by_component(self, component: str) -> List[MeshNode]:
        """Get all nodes running a specific component."""
        return [node for node in self.nodes.values() if node.component == component]
    
    def get_healthy_nodes(self) -> List[MeshNode]:
        """Get all healthy nodes."""
        return [node for node in self.nodes.values() if node.status == NodeStatus.HEALTHY]
    
    def get_mesh_status(self) -> Dict[str, Any]:
        """Get overall mesh status."""
        healthy = len(self.get_healthy_nodes())
        total = len(self.nodes)
        
        return {
            "total_nodes": total,
            "healthy_nodes": healthy,
            "unhealthy_nodes": total - healthy,
            "nodes": {
                node_id: {
                    "component": node.component,
                    "platform": node.platform,
                    "status": node.status.value,
                    "last_health_check": node.last_health_check
                }
                for node_id, node in self.nodes.items()
            }
        }
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
