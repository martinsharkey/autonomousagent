"""
Daemon Cluster - Multi-instance coordination for survivability.

Enables the council to run across multiple locations simultaneously,
like atoms in a molecule — each instance is a valid copy that can
take over if others fail.

Architecture:
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │  Instance A │────▶│  Shared Git  │◀────│  Instance B │
  │  (primary)  │     │  + State DB  │     │  (replica)  │
  └─────────────┘     └─────────────┘     └─────────────┘
         │                                        │
         └──────── Heartbeat Protocol ────────────┘

Coordination Model:
- All instances share state via git (code) + SQLite replication (memory/goals)
- Leader election via heartbeat (oldest healthy instance leads)
- Non-leaders run in "warm standby" — they observe but don't mutate
- If leader goes silent (missed heartbeats), next instance promotes itself
- Mutations only happen on the leader; replicas apply them via git pull + hot-reload

Survivability Properties:
- Any single instance can reconstruct full state from git + db
- No shared infrastructure required (each instance brings its own compute)
- Instances can be on different providers (Render, Railway, Fly.io, etc.)
- Leader failure recovery in < 60 seconds

Integration with Evolution Saga:
- Only the leader proposes/votes/promotes mutations
- Replicas hot-reload after leader pushes to git
- If leader dies mid-mutation, the new leader can rollback or re-apply
"""

import os
import time
import json
import asyncio
import hashlib
import platform
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class InstanceRole:
    LEADER = "leader"
    REPLICA = "replica"
    JOINING = "joining"
    DEAD = "dead"


class DaemonInstance:
    """Represents this daemon instance in the cluster."""
    
    def __init__(self):
        self.instance_id = self._generate_instance_id()
        self.role = InstanceRole.JOINING
        self.start_time = datetime.now(timezone.utc)
        self.last_heartbeat = self.start_time
        self.hostname = platform.node()
        self.pid = os.getpid()
        
        # Cluster coordination
        self.heartbeat_interval = int(os.getenv("CLUSTER_HEARTBEAT_INTERVAL", "15"))
        self.leader_timeout = int(os.getenv("CLUSTER_LEADER_TIMEOUT", "60"))
        self.state_file = PROJECT_ROOT / ".cluster_state.json"
        self.heartbeat_file = PROJECT_ROOT / ".cluster_heartbeats.json"
    
    def _generate_instance_id(self) -> str:
        """Generate a unique ID for this instance based on host + PID + start time."""
        raw = f"{platform.node()}:{os.getpid()}:{time.time()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    
    def get_identity(self) -> Dict[str, Any]:
        """Return this instance's identity for heartbeat registration."""
        return {
            "instance_id": self.instance_id,
            "hostname": self.hostname,
            "pid": self.pid,
            "role": self.role,
            "start_time": self.start_time.isoformat(),
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": (datetime.now(timezone.utc) - self.start_time).total_seconds(),
        }
    
    def is_leader(self) -> bool:
        return self.role == InstanceRole.LEADER
    
    def is_replica(self) -> bool:
        return self.role == InstanceRole.REPLICA


class ClusterCoordinator:
    """
    Coordinates multiple daemon instances for survivability.
    
    Uses a shared heartbeat file (synced via git or shared storage)
    to track which instances are alive and elect a leader.
    """
    
    def __init__(self, instance: DaemonInstance):
        self.instance = instance
        self.known_instances: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start cluster coordination."""
        self._running = True
        self._load_cluster_state()
        self._register_self()
        await self._elect_leader()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        print(f"[CLUSTER] Instance {self.instance.instance_id[:8]} started as {self.instance.role}")
    
    async def stop(self):
        """Gracefully leave the cluster."""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        self._deregister_self()
        self._save_cluster_state()
        print(f"[CLUSTER] Instance {self.instance.instance_id[:8]} stopped")
    
    def _load_cluster_state(self):
        """Load known cluster state from shared file."""
        if self.instance.heartbeat_file.exists():
            try:
                with open(self.instance.heartbeat_file, 'r') as f:
                    data = json.load(f)
                self.known_instances = data.get("instances", {})
            except (json.JSONDecodeError, IOError):
                self.known_instances = {}
    
    def _save_cluster_state(self):
        """Persist cluster state to shared file."""
        data = {
            "instances": self.known_instances,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "leader": self._get_current_leader_id(),
        }
        try:
            with open(self.instance.heartbeat_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            print(f"[CLUSTER] Failed to save state: {e}")
    
    def _register_self(self):
        """Register this instance in the cluster."""
        self.known_instances[self.instance.instance_id] = self.instance.get_identity()
        self._save_cluster_state()
    
    def _deregister_self(self):
        """Remove self from cluster on graceful shutdown."""
        self.known_instances.pop(self.instance.instance_id, None)
        self._save_cluster_state()
    
    def _get_current_leader_id(self) -> Optional[str]:
        """Get the current leader's instance ID."""
        for iid, info in self.known_instances.items():
            if info.get("role") == InstanceRole.LEADER:
                return iid
        return None
    
    def _get_alive_instances(self) -> Dict[str, Dict[str, Any]]:
        """Filter to instances with recent heartbeats."""
        now = datetime.now(timezone.utc)
        alive = {}
        for iid, info in self.known_instances.items():
            try:
                last_hb = datetime.fromisoformat(info["last_heartbeat"])
                age = (now - last_hb).total_seconds()
                if age < self.instance.leader_timeout:
                    alive[iid] = info
            except (KeyError, ValueError):
                continue
        return alive
    
    async def _elect_leader(self):
        """
        Leader election: oldest alive instance becomes leader.
        Simple but deterministic — all instances will agree.
        """
        alive = self._get_alive_instances()
        
        if not alive:
            # We're alone — become leader
            self.instance.role = InstanceRole.LEADER
            self.known_instances[self.instance.instance_id]["role"] = InstanceRole.LEADER
            self._save_cluster_state()
            return
        
        # Check if current leader is still alive
        current_leader = self._get_current_leader_id()
        if current_leader and current_leader in alive:
            # Leader is alive
            if current_leader == self.instance.instance_id:
                self.instance.role = InstanceRole.LEADER
            else:
                self.instance.role = InstanceRole.REPLICA
            return
        
        # No leader or leader is dead — elect by oldest start_time
        oldest_id = None
        oldest_time = None
        for iid, info in alive.items():
            try:
                start = datetime.fromisoformat(info["start_time"])
                if oldest_time is None or start < oldest_time:
                    oldest_time = start
                    oldest_id = iid
            except (KeyError, ValueError):
                continue
        
        if oldest_id == self.instance.instance_id:
            self.instance.role = InstanceRole.LEADER
            self.known_instances[self.instance.instance_id]["role"] = InstanceRole.LEADER
            print(f"[CLUSTER] This instance elected as LEADER (oldest alive)")
        else:
            self.instance.role = InstanceRole.REPLICA
            self.known_instances[self.instance.instance_id]["role"] = InstanceRole.REPLICA
        
        self._save_cluster_state()
    
    async def _heartbeat_loop(self):
        """Periodic heartbeat and leader health check."""
        while self._running:
            try:
                await asyncio.sleep(self.instance.heartbeat_interval)
                
                # Update our heartbeat
                self.instance.last_heartbeat = datetime.now(timezone.utc)
                if self.instance.instance_id in self.known_instances:
                    self.known_instances[self.instance.instance_id]["last_heartbeat"] = \
                        self.instance.last_heartbeat.isoformat()
                    self.known_instances[self.instance.instance_id]["role"] = self.instance.role
                
                # Reload cluster state (other instances may have written)
                self._load_cluster_state()
                # Re-register ourselves (in case file was overwritten)
                self.known_instances[self.instance.instance_id] = self.instance.get_identity()
                
                # Check leader health
                await self._elect_leader()
                
                # If we're leader, sync state to replicas via git
                if self.instance.is_leader():
                    await self._leader_sync()
                else:
                    # Replica: pull latest from git
                    await self._replica_pull()
                
                self._save_cluster_state()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[CLUSTER] Heartbeat error: {e}")
    
    async def _leader_sync(self):
        """Leader pushes state artifacts to git for replicas to consume."""
        # State is already pushed by evolution engine after mutations
        # This is for heartbeat file sync
        pass
    
    async def _replica_pull(self):
        """
        Replica pulls latest code from git and hot-reloads.
        Only pulls if there are new commits.
        """
        import subprocess
        try:
            result = subprocess.run(
                ["git", "fetch", "origin", "main", "--dry-run"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.stdout.strip() or result.stderr.strip():
                # There are new commits — pull and reload
                pull_result = subprocess.run(
                    ["git", "pull", "origin", "main", "--ff-only"],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                
                if pull_result.returncode == 0:
                    # Hot-reload changed modules
                    from core.hot_reload import reload_all_project_modules
                    reload_result = reload_all_project_modules()
                    print(f"[CLUSTER:REPLICA] Pulled and reloaded: {len(reload_result['reloaded'])} modules")
                    
        except Exception as e:
            print(f"[CLUSTER:REPLICA] Pull failed: {e}")
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get current cluster status for reporting."""
        alive = self._get_alive_instances()
        return {
            "this_instance": self.instance.instance_id[:8],
            "role": self.instance.role,
            "total_instances": len(self.known_instances),
            "alive_instances": len(alive),
            "leader": self._get_current_leader_id(),
            "instances": [
                {
                    "id": iid[:8],
                    "hostname": info.get("hostname", "unknown"),
                    "role": info.get("role", "unknown"),
                    "uptime": info.get("uptime_seconds", 0),
                }
                for iid, info in alive.items()
            ],
        }
    
    def should_run_evolution(self) -> bool:
        """Only the leader should propose/vote/promote mutations."""
        return self.instance.is_leader()
    
    def should_run_goals(self) -> bool:
        """Only the leader should execute goals."""
        return self.instance.is_leader()
    
    def should_respond_telegram(self) -> bool:
        """Only the leader should respond to Telegram messages."""
        return self.instance.is_leader()


# Global singleton
_cluster: Optional[ClusterCoordinator] = None
_instance: Optional[DaemonInstance] = None


def get_daemon_instance() -> DaemonInstance:
    """Get or create the daemon instance identity."""
    global _instance
    if _instance is None:
        _instance = DaemonInstance()
    return _instance


def get_cluster_coordinator() -> ClusterCoordinator:
    """Get or create the cluster coordinator."""
    global _cluster
    if _cluster is None:
        _cluster = ClusterCoordinator(get_daemon_instance())
    return _cluster


def is_leader() -> bool:
    """Quick check if this instance is the cluster leader."""
    if _cluster is None:
        return True  # Single instance mode = always leader
    return _cluster.instance.is_leader()
