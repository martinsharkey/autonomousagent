import requests
from typing import Optional, Dict, Any

class OllamaAdapter:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.timeout = 300

    def generate(self, model: str, prompt: str, **kwargs) -> Optional[str]:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    **kwargs
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Ollama generation failed: {str(e)}")
            return None

    def list_models(self) -> Optional[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Ollama model listing failed: {str(e)}")
            return None

    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False