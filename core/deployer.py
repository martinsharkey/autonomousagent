"""
Phase B: Deployment Packager

Takes a component function and wraps it as a standalone microservice
that can run on free platforms (HF Spaces, Replit, Railway, etc).
"""
import os
import json
import uuid
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from governance.audit_log import log_event


@dataclass
class ComponentSpec:
    """Specification for a deployable component."""
    name: str
    description: str
    entry_point: str  # Python function path, e.g., "core.sentiment.analyze"
    requirements: list = field(default_factory=list)
    environment_vars: list = field(default_factory=list)
    platform: str = "huggingface_spaces"
    health_path: str = "/health"
    task_path: str = "/task"
    callback_path: str = "/result"
    timeout_seconds: int = 30
    memory_mb: int = 512
    cpu_cores: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class DeploymentPackager:
    """Package council components as deployable microservices."""
    
    def __init__(self, output_dir: str = "deploy/components"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def package(self, spec: ComponentSpec) -> Path:
        """Package a component as a standalone service."""
        component_dir = self.output_dir / spec.name
        component_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate platform-specific files
        if spec.platform == "huggingface_spaces":
            self._generate_hf_spaces(component_dir, spec)
        elif spec.platform == "replit":
            self._generate_replit(component_dir, spec)
        elif spec.platform == "railway":
            self._generate_railway(component_dir, spec)
        else:
            self._generate_generic(component_dir, spec)
        
        # Always generate these
        self._generate_app_py(component_dir, spec)
        self._generate_requirements(component_dir, spec)
        self._generate_readme(component_dir, spec)
        
        log_event(
            "component_packaged",
            "deployer",
            "package",
            {
                "component": spec.name,
                "platform": spec.platform,
                "path": str(component_dir)
            }
        )
        
        return component_dir
    
    def _generate_hf_spaces(self, component_dir: Path, spec: ComponentSpec):
        """Generate HuggingFace Spaces specific files."""
        app_py = component_dir / "app.py"
        app_py.write_text(self._build_app_code(spec, hf_spaces=True))
        
        dockerfile = component_dir / "Dockerfile"
        dockerfile.write_text(f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]
""")
        
        readme = component_dir / "README.md"
        readme.write_text(f"""# {spec.name}

{spec.description}

## HuggingFace Space

This space runs the `{spec.name}` component for the autonomous council mesh.

## API

- POST /task - Submit task
- GET /health - Health check
""")
    
    def _generate_replit(self, component_dir: Path, spec: ComponentSpec):
        """Generate Replit specific files."""
        app_py = component_dir / "main.py"
        app_py.write_text(self._build_app_code(spec, replit=True))
        
        replit_config = component_dir / ".replit"
        replit_config.write_text(f"""run = ["python", "main.py"]
entrypoint = "main.py"
""")
    
    def _generate_railway(self, component_dir: Path, spec: ComponentSpec):
        """Generate Railway specific files."""
        app_py = component_dir / "app.py"
        app_py.write_text(self._build_app_code(spec, railway=True))
        
        railway_toml = component_dir / "railway.toml"
        railway_toml.write_text(f"""[build]
builder = "nixpacks"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "python app.py"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
""")
    
    def _generate_generic(self, component_dir: Path, spec: ComponentSpec):
        """Generate generic Docker-based deployment."""
        app_py = component_dir / "app.py"
        app_py.write_text(self._build_app_code(spec))
        
        dockerfile = component_dir / "Dockerfile"
        dockerfile.write_text(f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "app.py"]
""")
    
    def _generate_app_py(self, component_dir: Path, spec: ComponentSpec):
        """Generate the main application entry point."""
        app_py = component_dir / "app.py"
        app_py.write_text(self._build_app_code(spec))
    
    def _build_app_code(self, spec: ComponentSpec, hf_spaces: bool = False, 
                        replit: bool = False, railway: bool = False) -> str:
        """Build the application code for a component."""
        port = os.getenv("PORT", "8000")
        
        code = f'''"""
{spec.name} - Autonomous Council Microservice
Platform: {spec.platform}
Generated by Phase B Deployment Packager
"""
import os
import sys
import json
import uuid
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("{spec.name}")

# Configuration
NODE_ID = os.getenv("NODE_ID", f"{spec.name}-{{uuid.uuid4().hex[:8]}}")
COUNCIL_URL = os.getenv("COUNCIL_URL", "http://localhost:8000")
SHARED_SECRET = os.getenv("SHARED_SECRET", "")
PORT = int(os.getenv("PORT", "{port}"))

app = FastAPI(title="{spec.name}", version="1.0.0")

# Task models
class TaskRequest(BaseModel):
    task_id: str
    input: Dict[str, Any]
    callback_url: Optional[str] = None

class TaskResult(BaseModel):
    task_id: str
    node_id: str
    status: str
    result: Dict[str, Any]
    timestamp: str


# Import the actual component logic
try:
    from {spec.entry_point.rsplit(".", 1)[0]} import {spec.entry_point.rsplit(".", 1)[1]} as _component_func
    logger.info(f"Loaded component: {{spec.entry_point}}")
except Exception as e:
    logger.error(f"Failed to load component {{spec.entry_point}}: {{e}}")
    _component_func = None


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {{
        "node_id": NODE_ID,
        "component": "{spec.name}",
        "platform": "{spec.platform}",
        "status": "healthy",
        "uptime_seconds": 0,
        "timestamp": datetime.utcnow().isoformat()
    }}


@app.post("/task")
async def handle_task(request: TaskRequest):
    """Execute a task and optionally report result back to council."""
    if _component_func is None:
        raise HTTPException(status_code=500, detail="Component not loaded")
    
    logger.info(f"Executing task {{request.task_id}}")
    
    try:
        # Execute the component function
        if asyncio.iscoroutinefunction(_component_func):
            result = await _component_func(request.input)
        else:
            result = _component_func(request.input)
        
        response = TaskResult(
            task_id=request.task_id,
            node_id=NODE_ID,
            status="completed",
            result={{"output": result}},
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Report back to council if callback provided
        if request.callback_url:
            await _report_result(request.callback_url, response)
        
        return response
        
    except Exception as e:
        logger.error(f"Task {{request.task_id}} failed: {{e}}")
        raise HTTPException(status_code=500, detail=str(e))


async def _report_result(callback_url: str, result: TaskResult):
    """Report task result back to council."""
    try:
        async with httpx.AsyncClient(timeout={spec.timeout_seconds}) as client:
            response = await client.post(
                callback_url,
                json=result.dict(),
                headers={{"Content-Type": "application/json"}}
            )
            response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to report result: {{e}}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
'''
        return code
    
    def _generate_requirements(self, component_dir: Path, spec: ComponentSpec):
        """Generate requirements.txt for the component."""
        base_reqs = [
            "fastapi>=0.100.0",
            "uvicorn>=0.23.0",
            "pydantic>=2.0.0",
            "httpx>=0.24.0",
            "python-dotenv>=1.0.0",
        ]
        
        # Add component-specific requirements
        all_reqs = base_reqs + spec.requirements
        
        # Remove duplicates while preserving order
        seen = set()
        unique_reqs = []
        for req in all_reqs:
            req_name = req.split(">=")[0].split("==")[0].lower()
            if req_name not in seen:
                seen.add(req_name)
                unique_reqs.append(req)
        
        requirements = component_dir / "requirements.txt"
        requirements.write_text("\n".join(unique_reqs) + "\n")
    
    def _generate_readme(self, component_dir: Path, spec: ComponentSpec):
        """Generate README for the component."""
        readme = component_dir / "README.md"
        readme.write_text(f"""# {spec.name}

{spec.description}

## Deployment

Generated for platform: {spec.platform}

## API

- POST /task - Execute component function
- GET /health - Health check

## Environment Variables

- NODE_ID: Unique node identifier
- COUNCIL_URL: Main council URL for callbacks
- SHARED_SECRET: Authentication secret
- PORT: Server port (default: 8000)
""")


class DeploymentManager:
    """Manage deployments across platforms."""
    
    def __init__(self):
        self.packager = DeploymentPackager()
        self.active_deployments: Dict[str, Dict[str, Any]] = {}
    
    def deploy(self, spec: ComponentSpec) -> Dict[str, Any]:
        """Deploy a component to its target platform."""
        component_dir = self.packager.package(spec)
        
        deployment_record = {
            "component": spec.name,
            "platform": spec.platform,
            "path": str(component_dir),
            "status": "packaged",
            "timestamp": datetime.utcnow().isoformat(),
            "node_id": f"{spec.name}-{uuid.uuid4().hex[:8]}"
        }
        
        self.active_deployments[spec.name] = deployment_record
        
        log_event(
            "deployment_packaged",
            "deployer",
            "deploy",
            deployment_record
        )
        
        return deployment_record
    
    def get_deployment(self, component_name: str) -> Optional[Dict[str, Any]]:
        """Get deployment record for a component."""
        return self.active_deployments.get(component_name)
    
    def list_deployments(self) -> Dict[str, Dict[str, Any]]:
        """List all active deployments."""
        return dict(self.active_deployments)
