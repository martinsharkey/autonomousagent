#!/usr/bin/env python3
"""
Microbot: Free LLM Provider Researcher
Polls GitHub repos for free LLM provider updates and updates providers.yaml
"""

import asyncio
import json
import os
import sys
import yaml
from datetime import datetime, timezone
from pathlib import Path

try:
    import httpx
except ImportError:
    print("httpx not installed. Install with: pip install httpx")
    sys.exit(1)


GITHUB_REPOS = [
    "https://github.com/CYBIRD-D/FREE-LLM-API-Provider",
    "https://github.com/cheahjs/free-llm-api-resources",
    "https://github.com/Alishahryar1/free-llm-api-resources",
    "https://github.com/zebbern/no-cost-ai",
    "https://github.com/eudk/awesome-ai-tools",
]

PROVIDERS_FILE = Path("providers.yaml")
STATE_FILE = Path("microbot_llm_research_state.json")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_run": None, "known_providers": []}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def load_providers():
    if PROVIDERS_FILE.exists():
        with open(PROVIDERS_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("providers", [])
    return []


def save_providers(providers):
    with open(PROVIDERS_FILE, "w", encoding="utf-8") as f:
        yaml.dump({"providers": providers}, f, default_flow_style=False, sort_keys=False)


def extract_providers_from_readme(content: str, repo_url: str) -> list:
    """Extract provider entries from README content."""
    providers = []
    lines = content.split("\n")
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in ["api", "base url", "endpoint", "provider"]):
            context_start = max(0, i - 2)
            context_end = min(len(lines), i + 8)
            context = "\n".join(lines[context_start:context_end])
            
            if "http" in context and ("api" in context_lower or "openai" in context_lower):
                pass
    
    return providers


async def fetch_readme(repo_url: str) -> str | None:
    """Fetch README from GitHub repo."""
    repo_path = repo_url.replace("https://github.com/", "")
    api_url = f"https://api.github.com/repos/{repo_path}/readme"
    
    headers = {}
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(api_url, headers=headers)
            if response.status_code == 200:
                import base64
                data = response.json()
                content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                return content
            else:
                print(f"  Failed to fetch {repo_url}: {response.status_code}")
                return None
    except Exception as e:
        print(f"  Error fetching {repo_url}: {e}")
        return None


async def research_providers():
    """Research new free LLM providers from GitHub repos."""
    state = load_state()
    current_providers = load_providers()
    current_names = {p["name"] for p in current_providers}
    
    new_providers = []
    
    for repo_url in GITHUB_REPOS:
        print(f"Checking {repo_url}...")
        readme = await fetch_readme(repo_url)
        if readme:
            extracted = extract_providers_from_readme(readme, repo_url)
            for provider in extracted:
                name = provider.get("name", "")
                if name and name not in current_names and name not in state.get("known_providers", []):
                    new_providers.append(provider)
                    state.setdefault("known_providers", []).append(name)
    
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    
    if new_providers:
        print(f"\nFound {len(new_providers)} new providers:")
        for p in new_providers:
            print(f"  - {p.get('name')}: {p.get('base_url')}")
        
        current_providers.extend(new_providers)
        save_providers(current_providers)
        print(f"\nUpdated {PROVIDERS_FILE} with {len(new_providers)} new providers")
    else:
        print("\nNo new providers found")
    
    return new_providers


async def main():
    print("="*60)
    print("MICROBOT: Free LLM Provider Researcher")
    print("="*60)
    print(f"Run time: {datetime.now(timezone.utc).isoformat()}")
    print(f"Repos to check: {len(GITHUB_REPOS)}")
    print("="*60 + "\n")
    
    new_providers = await research_providers()
    
    print("\n" + "="*60)
    print("Research complete")
    print(f"New providers found: {len(new_providers)}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
