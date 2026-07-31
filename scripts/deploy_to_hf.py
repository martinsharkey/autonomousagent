#!/usr/bin/env python3
"""Deploy council daemon to HuggingFace Spaces (Docker SDK).

This deploys a Docker Space that runs the actual council_daemon.py process
in a background thread, with a FastAPI health endpoint on port 7860.

Usage:
    python scripts/deploy_to_hf.py [--space-name NAME] [--hf-username USERNAME]

Requires:
    - HF_API_KEY in .env or environment
    - huggingface_hub installed (pip install huggingface_hub)

After deploy, configure these Space Secrets in the HF UI:
    - COUNCIL_MASTER_KEY (your vault master passphrase)
    - HF_API_KEY (HuggingFace API token)
    - TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, etc. (as needed by the daemon)
"""

import os
import sys
import argparse
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Unlock vault if available (portable secrets)
try:
    from core.secrets_vault import get_vault
    _vault = get_vault()
    if _vault.is_unlocked:
        _vault.inject_into_environment()
except Exception:
    pass


def get_hf_token() -> str:
    token = os.getenv("HF_API_KEY") or os.getenv("HUGGINGFACE_TOKEN")
    if not token:
        print("ERROR: HF_API_KEY not set.")
        print("  Option 1: Add to .env: HF_API_KEY=hf_xxxxx")
        print("  Option 2: Store in vault: python -m core.secrets_vault")
        print("  Option 3: Export: export HF_API_KEY=hf_xxxxx")
        sys.exit(1)
    return token


def get_hf_username(token: str) -> str:
    """Get HF username from token."""
    try:
        from huggingface_hub import HfApi
        api = HfApi(token=token)
        info = api.whoami()
        return info["name"]
    except Exception as e:
        print(f"ERROR: Could not get HF username: {e}")
        sys.exit(1)


def create_space_files(deploy_dir: Path, space_name: str):
    """Create the files needed for the HF Space (Docker SDK - runs the real daemon)."""
    
    deploy_time = datetime.now(timezone.utc).isoformat()
    
    # app.py - Runs the council daemon in a background thread + serves health endpoints
    app_code = '''#!/usr/bin/env python3
import os
import sys
import time
import signal
import threading
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

DEPLOY_TIME = datetime.now(timezone.utc).isoformat()
START_TIME = time.time()

app = FastAPI(title="Council Daemon", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_daemon_thread = None
_daemon_started = False
_last_heartbeat = None


def _run_daemon():
    global _last_heartbeat
    try:
        sys.path.insert(0, "/workspace")
        from council_daemon import CouncilDaemon
        daemon = CouncilDaemon()
        daemon.run()
    except Exception as e:
        print(f"DAEMON ERROR: {e}", flush=True)


@app.on_event("startup")
async def startup_event():
    global _daemon_thread, _daemon_started
    if not _daemon_started:
        _daemon_thread = threading.Thread(target=_run_daemon, daemon=True)
        _daemon_thread.start()
        _daemon_started = True
        print("[DAEMON] Council daemon started in background thread", flush=True)


@app.get("/")
async def root():
    return {
        "service": "council-daemon",
        "status": "alive",
        "deployed_at": DEPLOY_TIME,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "daemon_started": _daemon_started,
    }


@app.get("/health")
async def health():
    uptime = round(time.time() - START_TIME, 1)
    return {
        "status": "alive",
        "deployed_at": DEPLOY_TIME,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime,
        "daemon_started": _daemon_started,
    }


@app.get("/status")
async def status():
    try:
        from core.goals import GoalStore
        store = GoalStore()
        goals = store.get_all_goals() if hasattr(store, 'get_all_goals') else []
        open_goals = store.get_open_goals() if hasattr(store, 'get_open_goals') else []
        return {
            "status": "alive",
            "deployed_at": DEPLOY_TIME,
            "daemon_started": _daemon_started,
            "uptime_seconds": round(time.time() - START_TIME, 1),
            "total_goals": len(goals),
            "open_goals": len(open_goals),
            "goals": [g if isinstance(g, dict) else g.__dict__ for g in goals[:10]],
        }
    except Exception as e:
        return {
            "status": "alive",
            "daemon_started": _daemon_started,
            "uptime_seconds": round(time.time() - START_TIME, 1),
            "error": str(e),
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
'''

    # requirements.txt for the Space runtime
    requirements = """fastapi>=0.100.0
uvicorn[standard]>=0.20.0
huggingface_hub>=0.20.0
python-dotenv>=1.0.0
langgraph>=0.2.0
langchain>=0.2.0
langchain-community>=0.2.0
langchain-core>=0.2.27
langchain-ollama>=0.1.0
pydantic>=2.9.0
ollama>=0.3.0
httpx>=0.27.0
aiohttp>=3.9.0
python-telegram-bot>=21.6
litellm>=1.0.0
sqlalchemy>=2.0.0
"""

    # Dockerfile
    dockerfile = """FROM python:3.12-slim

WORKDIR /workspace

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \\
    git \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app and core modules
COPY app.py .
COPY council_daemon.py .
COPY core/ core/
COPY agents/ agents/
COPY tools/ tools/
COPY governance/ governance/
COPY evolution/ evolution/

# Create required directories
RUN mkdir -p evolution agent_configs .keys logs

# Port for HF Spaces
EXPOSE 7860

# Secrets (COUNCIL_MASTER_KEY, API keys) come from HF Space Secrets
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
"""

    # README.md (HF Spaces metadata - Docker SDK)
    readme = f"""---
title: Council Daemon
emoji: 🧠
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
---

# Council Daemon — HuggingFace Spaces

The autonomous 3-agent council (autobot, alpha_evaluator, beta_worker) running 24/7 with durable state.

## Status
- **Deployed:** {deploy_time}
- **Runtime:** Docker (Python 3.12-slim)
- **Free Tier:** Docker Spaces requires HF PRO — if unavailable, the static heartbeat at `/spaces/martysharkey/council-heartbeat` remains the fallback

## Endpoints
- `/` — Root status
- `/health` — Health check JSON
- `/status` — Detailed daemon status (goals, uptime)

## Source
[martysharkey/autonomousagent](https://github.com/martysharkey/autonomousagent)

## Required Space Secrets
```
COUNCIL_MASTER_KEY=Matthew-nathan-chris
HF_API_KEY=hf_xxxxx
TELEGRAM_BOT_TOKEN=xxxxx
TELEGRAM_CHAT_ID=xxxxx
```

## Purpose
Survivability proof — the council daemon runs beyond the operator's laptop, maintaining durable goals and state.
"""

    # Write files
    (deploy_dir / "app.py").write_text(app_code, encoding="utf-8")
    (deploy_dir / "requirements.txt").write_text(requirements, encoding="utf-8")
    (deploy_dir / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    (deploy_dir / "README.md").write_text(readme, encoding="utf-8")
    
    print(f"  Created: app.py, requirements.txt, Dockerfile, README.md (Docker SDK)")


def deploy_to_hf(space_name: str, token: str, username: str):
    """Deploy the space to HuggingFace."""
    from huggingface_hub import HfApi, create_repo
    
    repo_id = f"{username}/{space_name}"
    api = HfApi(token=token)
    
    print(f"\n🚀 Deploying to: https://huggingface.co/spaces/{repo_id}")
    
    # Create or get the space
    try:
        create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            token=token,
            exist_ok=True,
        )
        print(f"  ✓ Space '{repo_id}' ready")
    except Exception as e:
        print(f"  Creating space: {e}")
    
    # Create deployment files in a temp dir
    with tempfile.TemporaryDirectory() as tmpdir:
        deploy_dir = Path(tmpdir)
        create_space_files(deploy_dir, space_name)
        
        # Upload to HF
        print(f"  Uploading files...")
        api.upload_folder(
            folder_path=str(deploy_dir),
            repo_id=repo_id,
            repo_type="space",
            commit_message="Deploy council daemon service (Docker SDK)",
        )
    
    space_url = f"https://huggingface.co/spaces/{repo_id}"
    print(f"\n✅ Deployed successfully!")
    print(f"   URL: {space_url}")
    print(f"   Health: {space_url}/health")
    print(f"\n   Note: It may take 2-5 minutes for the Docker image to build and start.")
    
    return {"repo_id": repo_id, "url": space_url, "sdk": "docker", "status": "deployed"}


def main():
    parser = argparse.ArgumentParser(description="Deploy council to HuggingFace Spaces")
    parser.add_argument("--space-name", default="council-heartbeat", help="Name of the HF Space")
    parser.add_argument("--hf-username", default=None, help="HuggingFace username (auto-detected if not provided)")
    args = parser.parse_args()
    
    print("🧠 Council HuggingFace Spaces Deployer")
    print("=" * 40)
    
    token = get_hf_token()
    print(f"  ✓ HF_API_KEY found")
    
    username = args.hf_username or get_hf_username(token)
    print(f"  ✓ Username: {username}")
    
    result = deploy_to_hf(args.space_name, token, username)
    
    record_file = PROJECT_ROOT / "evolution" / "hf_deployment.json"
    record_file.parent.mkdir(parents=True, exist_ok=True)
    import json
    with open(record_file, "w") as f:
        json.dump({
            **result,
            "deployed_at": datetime.now(timezone.utc).isoformat(),
            "deployed_by": "operator",
        }, f, indent=2)
    print(f"\n  Deployment record saved to: {record_file}")


if __name__ == "__main__":
    main()
