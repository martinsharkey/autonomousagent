import httpx
import asyncio
from typing import Dict, List
from datetime import datetime

class HeartbeatManager:
    def __init__(self, interval_seconds: int = 300):
        self.interval = interval_seconds
        self.endpoints: Dict[str, str] = {}
        self.last_ping: Dict[str, datetime] = {}
        self.client = httpx.AsyncClient(timeout=10.0)
    
    def register_endpoint(self, name: str, url: str):
        self.endpoints[name] = url
        self.last_ping[name] = datetime.utcnow()
    
    def unregister_endpoint(self, name: str):
        if name in self.endpoints:
            del self.endpoints[name]
        if name in self.last_ping:
            del self.last_ping[name]
    
    async def ping_endpoint(self, name: str) -> bool:
        if name not in self.endpoints:
            return False
        
        url = self.endpoints[name]
        
        try:
            response = await self.client.get(url)
            self.last_ping[name] = datetime.utcnow()
            return response.status_code == 200
        except Exception as e:
            print(f"[HEARTBEAT] Ping failed for {name}: {e}")
            return False
    
    async def ping_all(self) -> Dict[str, bool]:
        results = {}
        for name in self.endpoints:
            results[name] = await self.ping_endpoint(name)
        return results
    
    async def wake_before_task(self, name: str) -> bool:
        success = await self.ping_endpoint(name)
        if not success:
            await asyncio.sleep(2)
            success = await self.ping_endpoint(name)
        return success
    
    def get_stale_endpoints(self, max_age_seconds: int = 900) -> List[str]:
        stale = []
        now = datetime.utcnow()
        for name, last_time in self.last_ping.items():
            age = (now - last_time).total_seconds()
            if age > max_age_seconds:
                stale.append(name)
        return stale
    
    async def close(self):
        await self.client.aclose()
