import os
import sys
import json
import uuid
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from core.deployer import DeploymentPackager, ComponentSpec
from governance.audit_log import log_event


@dataclass
class MicrobotSpec:
    name: str
    task_description: str
    entry_point: str
    requirements: list = field(default_factory=list)
    environment_vars: list = field(default_factory=list)
    platform: str = "local"
    timeout_seconds: int = 300
    memory_mb: int = 256
    cpu_cores: float = 0.5


@dataclass
class MicrobotInstance:
    instance_id: str
    spec: MicrobotSpec
    status: str = "starting"
    process: Optional[subprocess.Popen] = None
    deployment_path: Optional[Path] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class MicrobotSpawner:
    """Spawn task-specific microbot agents on free infrastructure."""

    def __init__(self, base_output_dir: str = "microbots/deployments"):
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        self.instances: Dict[str, MicrobotInstance] = {}
        self.packager = DeploymentPackager(output_dir=str(self.base_output_dir / "packages"))

    async def spawn(self, spec: MicrobotSpec) -> MicrobotInstance:
        """Spawn a microbot for the given task."""
        instance_id = f"microbot_{spec.name}_{uuid.uuid4().hex[:8]}"
        instance = MicrobotInstance(instance_id=instance_id, spec=spec)
        self.instances[instance_id] = instance

        try:
            if spec.platform == "local":
                await self._spawn_local(instance)
            else:
                await self._spawn_packaged(instance)
            instance.status = "running"
        except Exception as exc:
            instance.status = "failed"
            instance.error = str(exc)

        log_event(
            "microbot_spawned",
            "microbot_spawner",
            "spawn",
            {
                "instance_id": instance_id,
                "name": spec.name,
                "platform": spec.platform,
                "status": instance.status,
                "error": instance.error,
            },
        )
        return instance

    async def _spawn_local(self, instance: MicrobotInstance):
        """Spawn a local subprocess microbot."""
        spec = instance.spec
        script = f'''
import asyncio
import json
import sys
import os

async def main():
    print(json.dumps({{"status": "started", "instance_id": "{instance.instance_id}"}}))
    try:
        entry = "{spec.entry_point}"
        module_path, func_name = entry.rsplit(".", 1)
        sys.path.insert(0, os.getcwd())
        module = __import__(module_path, fromlist=[func_name])
        func = getattr(module, func_name)
        result = await func({{"task": {json.dumps(spec.task_description)}}})
        print(json.dumps({{"status": "completed", "result": result}}))
    except Exception as exc:
        print(json.dumps({{"status": "failed", "error": str(exc)}}))

if __name__ == "__main__":
    asyncio.run(main())
'''
        tmp_dir = Path(tempfile.mkdtemp(prefix=f"microbot_{spec.name}_"))
        script_path = tmp_dir / "run.py"
        script_path.write_text(script, encoding="utf-8")

        env = os.environ.copy()
        env.update({var.split("=", 1)[0]: var.split("=", 1)[1] for var in spec.environment_vars if "=" in var})

        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=Path.cwd(),
        )
        instance.process = process
        instance.deployment_path = tmp_dir

    async def _spawn_packaged(self, instance: MicrobotInstance):
        """Package and prepare a microbot for free platform deployment."""
        spec = instance.spec
        component_spec = ComponentSpec(
            name=spec.name,
            description=spec.task_description,
            entry_point=spec.entry_point,
            requirements=spec.requirements,
            environment_vars=spec.environment_vars,
            platform=spec.platform if spec.platform in {"huggingface_spaces", "replit", "railway"} else "huggingface_spaces",
            timeout_seconds=spec.timeout_seconds,
            memory_mb=spec.memory_mb,
            cpu_cores=spec.cpu_cores,
        )
        package_path = self.packager.package(component_spec)
        instance.deployment_path = package_path
        instance.status = "deployed"

    async def get_instance_status(self, instance_id: str) -> Optional[Dict[str, Any]]:
        instance = self.instances.get(instance_id)
        if not instance:
            return None

        if instance.process and instance.process.poll() is not None:
            instance.status = "completed" if instance.process.returncode == 0 else "failed"
            try:
                stdout = instance.process.stdout.read().decode("utf-8", errors="ignore").strip().splitlines() if instance.process.stdout else []
                for line in reversed(stdout):
                    if line.strip():
                        instance.result = {"raw_output": line}
                        break
            except Exception:
                pass

        return {
            "instance_id": instance.instance_id,
            "name": instance.spec.name,
            "platform": instance.spec.platform,
            "status": instance.status,
            "created_at": instance.created_at,
            "deployment_path": str(instance.deployment_path) if instance.deployment_path else None,
            "result": instance.result,
            "error": instance.error,
        }

    async def terminate(self, instance_id: str) -> bool:
        instance = self.instances.get(instance_id)
        if not instance:
            return False

        if instance.process and instance.process.poll() is None:
            instance.process.terminate()
            try:
                instance.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                instance.process.kill()
        instance.status = "terminated"
        return True

    def list_instances(self) -> List[Dict[str, Any]]:
        import asyncio
        loop = asyncio.get_event_loop()
        return [loop.run_until_complete(self.get_instance_status(iid)) for iid in self.instances]
