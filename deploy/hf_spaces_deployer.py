"""
Phase B: HuggingFace Spaces Deployer

Deploys council microservices to HuggingFace Spaces.
"""
import os
import json
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from core.deployer import ComponentSpec, DeploymentPackager, DeploymentManager
from governance.audit_log import log_event


class HuggingFaceSpacesDeployer:
    """Deploy microservices to HuggingFace Spaces."""
    
    def __init__(self, hf_token: Optional[str] = None):
        self.hf_token = hf_token or os.getenv("HF_API_KEY") or os.getenv("HUGGINGFACE_TOKEN")
        self.packager = DeploymentPackager()
        self.deployments: Dict[str, Dict[str, Any]] = {}
    
    def deploy(self, spec: ComponentSpec, space_name: Optional[str] = None) -> Dict[str, Any]:
        """Deploy a component to HF Spaces."""
        if not space_name:
            space_name = f"{spec.name}-council"
        
        # Package the component
        component_dir = self.packager.package(spec)
        
        # Create HF Space metadata
        self._create_space_metadata(component_dir, spec, space_name)
        
        # Create deployment record
        deployment = {
            "component": spec.name,
            "platform": "huggingface_spaces",
            "space_name": space_name,
            "space_url": f"https://huggingface.co/spaces/{space_name}",
            "status": "packaged",
            "path": str(component_dir),
            "timestamp": datetime.utcnow().isoformat(),
            "node_id": f"hf-{spec.name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        }
        
        self.deployments[spec.name] = deployment
        
        log_event(
            "hf_space_packaged",
            "hf_deployer",
            "deploy",
            deployment
        )
        
        return deployment
    
    def _create_space_metadata(self, component_dir: Path, spec: ComponentSpec, space_name: str):
        """Create HuggingFace Space metadata files."""
        # Create .space directory
        space_dir = component_dir / ".space"
        space_dir.mkdir(exist_ok=True)
        
        # Create space configuration
        space_config = {
            "title": spec.name,
            "sdk": "docker",
            "sdk_version": "latest",
            "app_file": "app.py"
        }
        
        with open(space_dir / "metadata.json", "w") as f:
            json.dump(space_config, f, indent=2)
        
        # Create README.md for HF Space
        readme = component_dir / "README.md"
        readme.write_text(f"""---
title: {spec.name}
sdk: docker
app_file: app.py
model: cpu
---

# {spec.name}

{spec.description}

## Autonomous Council Microservice

This microservice is part of the autonomous council mesh.

## API

- `POST /task` - Submit task for processing
- `GET /health` - Health check

## Usage

Send a POST request to `/task` with:
```json
{{
    "task_id": "unique-task-id",
    "input": {{...}}
}}
```
""")
    
    def get_status(self, space_name: str) -> Dict[str, Any]:
        """Get status of a deployed space."""
        return {
            "space_name": space_name,
            "url": f"https://huggingface.co/spaces/{space_name}",
            "status": "running",
            "platform": "huggingface_spaces"
        }
    
    async def deploy_live(self, spec: ComponentSpec, space_name: Optional[str] = None) -> Dict[str, Any]:
        """Deploy to HF Spaces via CLI (requires huggingface_hub)."""
        deployment = self.deploy(spec, space_name)
        
        try:
            # Try to use huggingface_hub if available
            from huggingface_hub import HfApi
            
            api = HfApi(token=self.hf_token)
            component_dir = Path(deployment["path"])
            
            # Create or update space
            space_id = deployment["space_name"]
            
            # Upload files
            api.upload_folder(
                folder_path=str(component_dir),
                repo_id=space_id,
                repo_type="space",
                commit_message=f"Deploy {spec.name} v1.0"
            )
            
            deployment["status"] = "deployed"
            deployment["deployed_at"] = datetime.utcnow().isoformat()
            
            log_event(
                "hf_space_deployed",
                "hf_deployer",
                "deploy_live",
                deployment
            )
            
        except ImportError:
            deployment["status"] = "packaged"
            deployment["note"] = "huggingface_hub not installed. Run: pip install huggingface_hub"
        except Exception as e:
            deployment["status"] = "error"
            deployment["error"] = str(e)
        
        return deployment
