import json
import hashlib
import time
from pathlib import Path

CACHE_DIR = Path('cache')
CACHE_TTL = 3600  # 1 hour

class RequestCache:
    def __init__(self, cache_dir: str = 'cache', ttl: int = CACHE_TTL):
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.cache_dir.mkdir(exist_ok=True)

    def _key(self, model: str, prompt: str, params: dict) -> str:
        payload = json.dumps({'model': model, 'prompt': prompt, 'params': params}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, model: str, prompt: str, params: dict):
        key = self._key(model, prompt, params)
        path = self.cache_dir / f'{key}.json'
        if not path.exists():
            return None
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            if time.time() - data['timestamp'] > self.ttl:
                path.unlink()
                return None
            return data['response']
        except Exception:
            return None

    def set(self, model: str, prompt: str, params: dict, response: str):
        key = self._key(model, prompt, params)
        path = self.cache_dir / f'{key}.json'
        data = {
            'timestamp': time.time(),
            'response': response
        }
        with open(path, 'w') as f:
            json.dump(data, f)

    def clear(self):
        for f in self.cache_dir.glob('*.json'):
            f.unlink()
