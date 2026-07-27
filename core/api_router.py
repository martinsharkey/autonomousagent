import os
import time
import yaml
import httpx
import sqlite3
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

_ROLE_MAP = {
    "human": "user",
    "ai": "assistant",
    "system": "system",
}


def _normalize_messages(messages: list) -> list:
    """Convert LangChain BaseMessage objects to OpenAI-compatible dicts."""
    normalized = []
    for msg in messages:
        if hasattr(msg, "type"):
            role = _ROLE_MAP.get(msg.type, msg.type)
            data = {
                "role": role,
                "content": getattr(msg, "content", "") or "",
            }
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                data["tool_calls"] = msg.tool_calls
            if hasattr(msg, "name") and getattr(msg, "name", None):
                data["name"] = msg.name
            normalized.append(data)
        elif isinstance(msg, dict) and "role" in msg:
            normalized.append(msg)
        else:
            normalized.append({"role": "user", "content": str(msg)})
    return normalized


def _provider_temperature(provider_name: str, fallback_temperature: float = 0.2) -> float:
    try:
        from core.provider_benchmark import get_provider_temperature
        return get_provider_temperature(provider_name)
    except Exception:
        return fallback_temperature


class LLMProviderPool:
    """Cloud-first LLM router with weighted round-robin and cooldown management."""
    
    def __init__(self, config_path: str = "providers.yaml"):
        self.config_path = config_path
        self.providers = []
        self.local_ollama = None
        self.router_config = {}
        self.cooldowns = {}  # provider_name -> cooldown_until timestamp
        self.stats = {}  # provider_name -> {success, failures, last_used}
        self.current_index = 0
        self._recalibration_lock = {}
        self._benchmark_pending = False
        
        self._load_config()
        self._init_stats_db()
        self.client = httpx.AsyncClient(timeout=self.router_config.get('timeout_seconds', 60))
    
    def _needs_auto_benchmark(self) -> bool:
        try:
            from core.provider_benchmark import load_settings
            settings = load_settings()
            cached_names = set(settings.get("providers", {}).keys())
            config_names = {p["name"] for p in self.providers}
            missing = config_names - cached_names
            if missing:
                return True
            last_benchmark = settings.get("last_benchmark")
            if not last_benchmark:
                return True
            try:
                last_dt = datetime.fromisoformat(last_benchmark)
                if datetime.utcnow() - last_dt > timedelta(hours=24):
                    return True
            except Exception:
                return True
        except Exception:
            return False
        return False

    def _trigger_auto_benchmark(self):
        if getattr(self, '_auto_benchmark_triggered', False) or self._benchmark_pending:
            return
        self._benchmark_pending = True
        self._auto_benchmark_triggered = True
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(self._run_auto_benchmark())
        except RuntimeError:
            self._benchmark_pending = False
        except Exception:
            self._benchmark_pending = False

    async def _run_auto_benchmark(self):
        try:
            from core.provider_benchmark import load_settings, save_settings, benchmark_provider
            settings = load_settings()
            cached_names = set(settings.get("providers", {}).keys())
            config_names = {p["name"] for p in self.providers}
            missing = sorted(config_names - cached_names)
            stale = False
            last_benchmark = settings.get("last_benchmark")
            if last_benchmark:
                try:
                    last_dt = datetime.fromisoformat(last_benchmark)
                    if datetime.utcnow() - last_dt > timedelta(hours=24):
                        stale = True
                except Exception:
                    stale = True
            else:
                stale = True

            targets = missing if not stale else sorted(config_names)
            if not targets:
                self._benchmark_pending = False
                return

            print(f"[API ROUTER] Auto-benchmarking providers: {', '.join(targets)}")
            for provider in self.providers:
                if provider["name"] not in targets:
                    continue
                api_key = os.getenv(provider["api_key_env"])
                if not api_key or "your-" in api_key:
                    continue
                best = await benchmark_provider(
                    provider_name=provider["name"],
                    base_url=provider["base_url"],
                    api_key=api_key,
                    model=provider["default_model"],
                    path=provider.get("path", "chat/completions"),
                )
                settings.setdefault("providers", {})
                settings["providers"][provider["name"]] = {
                    "temperature": best["temperature"],
                    "context": best["context"],
                    "model": provider["default_model"],
                    "base_url": provider["base_url"],
                }
            settings["last_benchmark"] = datetime.utcnow().isoformat()
            save_settings(settings)
            print("[API ROUTER] Provider benchmark complete")
        except Exception as exc:
            print(f"[API ROUTER] Auto-benchmark skipped: {exc}")
        finally:
            self._benchmark_pending = False
    
    def _load_config(self):
        """Load provider configuration from YAML."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.providers = config.get('providers', [])
                self.local_ollama = config.get('local_ollama', {})
                self.router_config = config.get('router', {})
        else:
            print(f"[API ROUTER] Warning: {self.config_path} not found")
    
    def _init_stats_db(self):
        """Initialize SQLite database for provider stats."""
        self.db_path = "llm_provider_stats.db"
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS provider_stats (
                provider TEXT PRIMARY KEY,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                last_used TEXT,
                cooldown_until TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def _get_active_providers(self) -> List[Dict]:
        """Get providers with valid API keys and not in cooldown."""
        active = []
        now = datetime.utcnow()
        
        for provider in self.providers:
            api_key = os.getenv(provider['api_key_env'])
            if not api_key:
                continue
            
            # Check cooldown
            cooldown_until = self.cooldowns.get(provider['name'])
            if cooldown_until and now < cooldown_until:
                continue
            
            active.append(provider)
        
        # Sort by weight (descending) for weighted round-robin
        active.sort(key=lambda p: p.get('weight', 5), reverse=True)
        return active
    
    def _select_provider(self) -> Optional[Dict]:
        """Select next provider using weighted round-robin."""
        active = self._get_active_providers()
        if not active:
            return None
        
        # Weighted selection: repeat providers by weight
        weighted_pool = []
        for provider in active:
            weight = provider.get('weight', 5)
            weighted_pool.extend([provider] * weight)
        
        if not weighted_pool:
            return None
        
        # Round-robin through weighted pool
        selected = weighted_pool[self.current_index % len(weighted_pool)]
        self.current_index += 1
        
        return selected
    
    def _set_cooldown(self, provider_name: str, seconds: int):
        """Set cooldown for a provider."""
        cooldown_until = datetime.utcnow() + timedelta(seconds=seconds)
        self.cooldowns[provider_name] = cooldown_until
        
        # Persist to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO provider_stats (provider, cooldown_until)
            VALUES (?, ?)
        ''', (provider_name, cooldown_until.isoformat()))
        conn.commit()
        conn.close()
        
        print(f"[API ROUTER] {provider_name} in cooldown for {seconds}s")
    
    def _record_success(self, provider_name: str):
        """Record successful API call."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO provider_stats (provider, success_count, last_used)
            VALUES (?, COALESCE((SELECT success_count FROM provider_stats WHERE provider = ?), 0) + 1, ?)
        ''', (provider_name, provider_name, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
    
    def _record_failure(self, provider_name: str):
        """Record failed API call."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO provider_stats (provider, failure_count, last_used)
            VALUES (?, COALESCE((SELECT failure_count FROM provider_stats WHERE provider = ?), 0) + 1, ?)
        ''', (provider_name, provider_name, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
    
    async def route_request(
        self,
        messages: list,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Route request through cloud providers with round-robin and failover."""
        if self._needs_auto_benchmark():
            self._trigger_auto_benchmark()
        
        max_retries = self.router_config.get('max_retries', 3)
        
        for attempt in range(max_retries):
            provider = self._select_provider()
            if not provider:
                if self.local_ollama and self.local_ollama.get('enabled') and self._is_local_ollama_available():
                    print("[API ROUTER] No cloud providers available, trying local Ollama")
                    return await self._call_local_ollama(messages, max_tokens, temperature)
                raise RuntimeError("No LLM providers available")
            
            provider_name = provider['name']
            print(f"[API ROUTER] Attempt {attempt + 1}: Using {provider_name} ({provider['default_model']})")
            
            try:
                result = await self._call_provider(provider, messages, max_tokens, temperature)
                self._record_success(provider_name)
                return result
            except httpx.HTTPStatusError as e:
                self._record_failure(provider_name)
                
                if e.response.status_code == 429:
                    cooldown = self.router_config.get('cooldown_429_seconds', 300)
                    self._set_cooldown(provider_name, cooldown)
                    print(f"[API ROUTER] {provider_name} rate limited (429), trying next")
                else:
                    cooldown = self.router_config.get('cooldown_error_seconds', 60)
                    self._set_cooldown(provider_name, cooldown)
                    print(f"[API ROUTER] {provider_name} failed with {e.response.status_code}, trying next")
            except Exception as e:
                self._record_failure(provider_name)
                cooldown = self.router_config.get('cooldown_error_seconds', 60)
                self._set_cooldown(provider_name, cooldown)
                print(f"[API ROUTER] {provider_name} error: {e}, trying next")
        
        # All retries failed
        if self.local_ollama and self.local_ollama.get('enabled') and self._is_local_ollama_available():
            print("[API ROUTER] All cloud providers failed, falling back to local Ollama")
            return await self._call_local_ollama(messages, max_tokens, temperature)
        
        raise RuntimeError("All LLM providers failed after max retries")
    
    async def _call_provider(
        self,
        provider: Dict,
        messages: list,
        max_tokens: Optional[int],
        temperature: float
    ) -> Dict[str, Any]:
        """Make API call to a specific provider."""
        api_key = os.getenv(provider['api_key_env'])
        base_url = provider['base_url']
        model = provider['default_model']
        path = provider.get('path', 'chat/completions')
        provider_name = provider.get('name', 'unknown')
        
        # Use cached provider-specific temperature unless caller explicitly overrides
        requested_temperature = temperature
        cached_temperature = _provider_temperature(provider_name)
        if requested_temperature == 0.7:
            temperature = cached_temperature
        else:
            temperature = requested_temperature
        
        # Handle special URL patterns
        if '{account_id}' in base_url:
            account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID', '')
            base_url = base_url.replace('{account_id}', account_id)
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        normalized_messages = _normalize_messages(messages)
        payload = {
            "model": model,
            "messages": normalized_messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        # Different providers use different paths
        if path == 'chat/completions':
            url = f"{base_url}/chat/completions"
        elif path == 'v1/openai/chat/completions':
            url = f"{base_url}/v1/openai/chat/completions"
        elif path == 'models':
            # HuggingFace uses different format
            url = f"{base_url}/{model}"
            payload.pop('model', None)  # Model is in URL
        else:
            url = f"{base_url}/{path}"
        
        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code if e.response else 0
            if status in (400, 401, 403, 500, 502, 503, 504):
                await self._maybe_recalibrate_provider(provider_name, provider)
            raise
    
    async def _call_local_ollama(
        self,
        messages: list,
        max_tokens: Optional[int],
        temperature: float
    ) -> Dict[str, Any]:
        """Fallback to local Ollama if reachable."""
        if not self._is_local_ollama_available():
            raise RuntimeError("Local Ollama is configured but not reachable")
        
        base_url = os.getenv('OLLAMA_BASE_URL', self.local_ollama.get('default_url', 'http://localhost:11434'))
        model = self.local_ollama.get('models', ['qwen3.5:4b'])[0]
        
        headers = {"Content-Type": "application/json"}
        normalized_messages = _normalize_messages(messages)
        payload = {
            "model": model,
            "messages": normalized_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        url = f"{base_url}/api/chat"
        response = await self.client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        ollama_response = response.json()
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": ollama_response.get('message', {}).get('content', '')
                }
            }]
        }
    
    def _is_local_ollama_available(self) -> bool:
        import socket
        base_url = os.getenv('OLLAMA_BASE_URL', self.local_ollama.get('default_url', 'http://localhost:11434') if self.local_ollama else 'http://localhost:11434')
        host = base_url.replace('http://', '').replace('https://', '').split(':')[0]
        port = 11434
        if ':' in base_url.replace('http://', '').replace('https://', ''):
            try:
                port = int(base_url.split(':')[-1].split('/')[0])
            except ValueError:
                pass
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except OSError:
            return False
    
    async def _maybe_recalibrate_provider(self, provider_name: str, provider: Dict):
        now = datetime.utcnow().timestamp()
        last = self._recalibration_lock.get(provider_name, 0.0)
        if (now - last) < 3600:
            return
        self._recalibration_lock[provider_name] = now

        try:
            from core.provider_benchmark import benchmark_provider, load_settings, save_settings
            api_key = os.getenv(provider['api_key_env'])
            if not api_key or 'your-' in api_key:
                return
            best = await benchmark_provider(
                provider_name=provider_name,
                base_url=provider['base_url'],
                api_key=api_key,
                model=provider['default_model'],
                path=provider.get('path', 'chat/completions'),
            )
            settings = load_settings()
            settings.setdefault('providers', {})
            settings['providers'][provider_name] = {
                'temperature': best['temperature'],
                'context': best['context'],
                'model': provider['default_model'],
                'base_url': provider['base_url'],
            }
            save_settings(settings)
            print(f"[API ROUTER] Recalibrated {provider_name}: {best}")
        except Exception as exc:
            print(f"[API ROUTER] Recalibration failed for {provider_name}: {exc}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get router status and provider health."""
        active = self._get_active_providers()
        total = len(self.providers)
        
        return {
            "backend": self.router_config.get('backend', 'cloud'),
            "active_providers": len(active),
            "total_providers": total,
            "cooldowns": {k: v.isoformat() for k, v in self.cooldowns.items()},
            "local_ollama_enabled": self.local_ollama.get('enabled', False)
        }
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Backward compatibility wrapper
class APIRouter(LLMProviderPool):
    """Backward-compatible API router using new provider pool."""
    
    async def route_request(
        self,
        messages: list,
        provider: str = "google",
        max_tokens: Optional[int] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Route request (ignores provider parameter, uses round-robin)."""
        return await super().route_request(messages, max_tokens, temperature)


# Global instance
_router_instance: Optional[LLMProviderPool] = None


def get_llm_router() -> LLMProviderPool:
    """Get or create the global LLM router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMProviderPool()
    return _router_instance
