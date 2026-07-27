"""
Phase B: Replit Deployer

Deploys council microservices to Replit.
"""
import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from core.deployer import ComponentSpec, DeploymentPackager
from governance.audit_log import log_event


class ReplitDeployer:
    """Deploy microservices to Replit."""
    
    def __init__(self, replit_token: Optional[str] = None):
        self.replit_token = replit_token or os.getenv("REPLIT_TOKEN")
        self.packager = DeploymentPackager()
        self.deployments: Dict[str, Dict[str, Any]] = {}
    
    def deploy(self, spec: ComponentSpec, repl_name: Optional[str] = None) -> Dict[str, Any]:
        """Deploy a component to Replit."""
        if not repl_name:
            repl_name = f"{spec.name}-council"
        
        # Package the component
        component_dir = self.packager.package(spec)
        
        # Create Replit-specific configuration
        self._create_replit_config(component_dir, spec, repl_name)
        
        # Create deployment record
        deployment = {
            "component": spec.name,
            "platform": "replit",
            "repl_name": repl_name,
            "repl_url": f"https://replit.com/@{os.getenv('REPLIT_USER', 'user')}/{repl_name}",
            "status": "packaged",
            "path": str(component_dir),
            "timestamp": datetime.utcnow().isoformat(),
            "node_id": f"replit-{spec.name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        }
        
        self.deployments[spec.name] = deployment
        
        log_event(
            "replit_packaged",
            "replit_deployer",
            "deploy",
            deployment
        )
        
        return deployment
    
    def _create_replit_config(self, component_dir: Path, spec: ComponentSpec, repl_name: str):
        """Create Replit-specific configuration files."""
        # .replit config
        replit_config = component_dir / ".replit"
        replit_config.write_text(f"""run = ["python", "main.py"]
entrypoint = "main.py"
modules = ["python3-11"]
""")
        
        # replit.nix for dependencies
        nix_config = component_dir / "replit.nix"
        nix_config.write_text(f"""{{ pkgs }}: {{
  pkgs = import pkgs;
  deps = [
    pkgs.python311
    pkgs.python311Packages.pip
  ];
}}
""")
        
        # Update requirements to include mesh communication
        requirements = component_dir / "requirements.txt"
        if requirements.exists():
            content = requirements.read_text()
            if "fastapi" not in content:
                content += "\nfastapi>=0.100.0\nuvicorn>=0.23.0\n"
            if "python-dotenv" not in content:
                content += "python-dotenv>=1.0.0\n"
            requirements.write_text(content)
    
    def get_status(self, repl_name: str) -> Dict[str, Any]:
        """Get status of a deployed Repl."""
        return {
            "repl_name": repl_name,
            "url": f"https://replit.com/@{os.getenv('REPLIT_USER', 'user')}/{repl_name}",
            "status": "running",
            "platform": "replit"
        }
