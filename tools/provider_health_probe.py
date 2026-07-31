import asyncio
import time
import json
import os
from typing import Dict, List, Optional

# Simple async HTTP client using asyncio streams to avoid external deps
async def probe_provider(name: str, url: str, timeout: float = 5.0) -> Dict:
    start = time.time()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(url.split('//')[1].split(':')[0], 443, ssl=True),
            timeout=timeout
        )
        # Send a minimal HTTP GET request
        request = f"GET / HTTP/1.1\r\nHost: {url.split('//')[1].split('/')[0]}\r\nConnection: close\r\n\r\n"
        writer.write(request.encode())
        await writer.drain()
        response = await asyncio.wait_for(reader.read(1024), timeout=timeout)
        writer.close()
        await writer.wait_closed()
        latency = time.time() - start
        return {"provider": name, "reachable": True, "latency_ms": round(latency * 1000, 2), "status": "ok"}
    except Exception as e:
        latency = time.time() - start
        return {"provider": name, "reachable": False, "latency_ms": round(latency * 1000, 2), "error": str(e), "status": "unreachable"}

async def run_probe(providers: Optional[Dict[str, str]] = None) -> List[Dict]:
    if providers is None:
        # Default providers from env or common endpoints
        providers = {
            "openai": os.getenv("OPENAI_ENDPOINT", "https://api.openai.com"),
            "anthropic": os.getenv("ANTHROPIC_ENDPOINT", "https://api.anthropic.com"),
            "google": os.getenv("GOOGLE_ENDPOINT", "https://generativelanguage.googleapis.com"),
            "local": os.getenv("LOCAL_ENDPOINT", "http://localhost:11434")
        }
    tasks = [probe_provider(name, url) for name, url in providers.items()]
    results = await asyncio.gather(*tasks)
    return results

def save_probe_results(results: List[Dict], log_path: str = "data/provider_probe_log.jsonl"):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

def main():
    results = asyncio.run(run_probe())
    save_probe_results(results)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
