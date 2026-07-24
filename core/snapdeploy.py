import httpx
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

SNAPDEPLOY_API_URL = "https://snapdeploy.io/api/v1"
SNAPDEPLOY_API_KEY = os.getenv("SNAPDEPLOY_API_KEY")

class SnapDeployManager:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.api_key = SNAPDEPLOY_API_KEY
        self.deployments: Dict[str, Dict] = {}
    
    async def create_deployment(self, dockerfile_content: str, name: str) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "SNAPDEPLOY_API_KEY not configured"}
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "name": name,
            "dockerfile": dockerfile_content,
            "auto_sleep": True,
            "auto_wake": True
        }
        
        try:
            response = await self.client.post(
                f"{SNAPDEPLOY_API_URL}/deployments",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            self.deployments[name] = result
            return result
        except httpx.HTTPError as e:
            return {"error": f"Deployment failed: {str(e)}"}
    
    async def wake_deployment(self, deployment_name: str) -> bool:
        if deployment_name not in self.deployments:
            return False
        
        deployment = self.deployments[deployment_name]
        wake_url = deployment.get("wake_url")
        
        if not wake_url:
            return False
        
        try:
            response = await self.client.get(wake_url, timeout=10.0)
            return response.status_code == 200
        except Exception as e:
            print(f"[SNAPDEPLOY] Wake failed for {deployment_name}: {e}")
            return False
    
    async def get_deployment_status(self, deployment_name: str) -> Optional[Dict]:
        if not self.api_key:
            return None
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            response = await self.client.get(
                f"{SNAPDEPLOY_API_URL}/deployments/{deployment_name}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[SNAPDEPLOY] Status check failed: {e}")
            return None
    
    async def delete_deployment(self, deployment_name: str) -> bool:
        if not self.api_key:
            return False
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            response = await self.client.delete(
                f"{SNAPDEPLOY_API_URL}/deployments/{deployment_name}",
                headers=headers
            )
            response.raise_for_status()
            if deployment_name in self.deployments:
                del self.deployments[deployment_name]
            return True
        except Exception as e:
            print(f"[SNAPDEPLOY] Delete failed: {e}")
            return False
    
    async def close(self):
        await self.client.aclose()

def generate_worker_dockerfile(model_name: str = "deepseek-coder:1.3b") -> str:
    return f"""FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir ollama langchain langchain-community httpx

COPY . /app

ENV OLLAMA_MODEL={model_name}

CMD ["python", "worker.py"]
"""
