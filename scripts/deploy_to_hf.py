#!/usr/bin/env python3
"""Deploy council heartbeat service to HuggingFace Spaces.

This deploys a minimal FastAPI service that:
1. Reports council health status
2. Syncs with the GitHub repo
3. Can receive commands from the operator via Telegram
4. Proves survivability (council exists beyond the laptop)

Usage:
    python scripts/deploy_to_hf.py [--space-name NAME] [--hf-username USERNAME]

Requires:
    - HF_API_KEY in .env or environment
    - huggingface_hub installed (pip install huggingface_hub)
"""

import os
import sys
import argparse
import tempfile
import shutil
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def get_hf_token() -> str:
    token = os.getenv("HF_API_KEY") or os.getenv("HUGGINGFACE_TOKEN")
    if not token:
        print("ERROR: HF_API_KEY not set. Add it to .env: HF_API_KEY=hf_xxxxx")
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
    """Create the files needed for the HF Space."""
    
    # app.py - the main FastAPI application
    app_code = '''#!/usr/bin/env python3
"""Council Heartbeat Service - HuggingFace Spaces deployment.

Minimal survivability service that:
- Reports council health
- Exposes a webhook for Telegram forwarding
- Can pull latest code from GitHub
"""

import os
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="Council Heartbeat", version="1.0.0")

# State
DEPLOY_TIME = datetime.now(timezone.utc).isoformat()
HEALTH_LOG = []


@app.get("/", response_class=HTMLResponse)
async def root():
    """Dashboard showing council status."""
    uptime = datetime.now(timezone.utc).isoformat()
    return f"""
    <html>
    <head><title>Council Heartbeat</title></head>
    <body style="font-family: monospace; background: #1a1a2e; color: #e0e0e0; padding: 2em;">
        <h1>🧠 Council Heartbeat Service</h1>
        <p><strong>Status:</strong> <span style="color: #4caf50;">ALIVE</span></p>
        <p><strong>Deployed:</strong> {DEPLOY_TIME}</p>
        <p><strong>Current UTC:</strong> {uptime}</p>
        <p><strong>Purpose:</strong> Survivability proof — council exists beyond operator's laptop</p>
        <hr>
        <h2>Endpoints</h2>
        <ul>
            <li><a href="/health">/health</a> — JSON health check</li>
            <li><a href="/status">/status</a> — Detailed status</li>
            <li><a href="/sync">/sync</a> — Trigger git pull</li>
        </ul>
    </body>
    </html>
    """


@app.get("/health")
async def health():
    """Health check endpoint for monitoring."""
    return {
        "status": "alive",
        "deployed_at": DEPLOY_TIME,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "service": "council-heartbeat",
        "version": "1.0.0",
    }


@app.get("/status")
async def status():
    """Detailed status with environment info."""
    return {
        "status": "alive",
        "deployed_at": DEPLOY_TIME,
        "environment": "huggingface_spaces",
        "python_version": subprocess.getoutput("python --version"),
        "disk_free": subprocess.getoutput("df -h / | tail -1"),
        "recent_health_checks": HEALTH_LOG[-10:],
    }


@app.get("/sync")
async def sync():
    """Pull latest code from GitHub (if git repo is available)."""
    try:
        result = subprocess.run(
            ["git", "pull", "--rebase"],
            capture_output=True, text=True, timeout=30
        )
        return {
            "action": "git_pull",
            "success": result.returncode == 0,
            "stdout": result.stdout[:500],
            "stderr": result.stderr[:500],
        }
    except Exception as e:
        return {"action": "git_pull", "success": False, "error": str(e)}


@app.post("/webhook")
async def webhook(request: Request):
    """Receive webhook notifications (e.g., from Telegram bot forwarding)."""
    try:
        body = await request.json()
        HEALTH_LOG.append({
            "type": "webhook",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload_keys": list(body.keys()) if isinstance(body, dict) else "non-dict",
        })
        return {"received": True}
    except Exception as e:
        return {"received": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
'''
    
    # requirements.txt
    requirements = """fastapi>=0.100.0
uvicorn[standard]>=0.20.0
"""
    
    # README.md (HF Spaces metadata)
    readme = f"""---
title: Council Heartbeat
emoji: 🧠
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
---

# Council Heartbeat Service

Minimal survivability service for the autonomous 3-agent council.

- **Health endpoint**: `/health`
- **Status dashboard**: `/`
- **Git sync**: `/sync`
- **Webhook receiver**: `/webhook` (POST)

Deployed automatically by the council's deployment pipeline.
"""
    
    # Dockerfile
    dockerfile = """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
"""
    
    # Write all files
    (deploy_dir / "app.py").write_text(app_code)
    (deploy_dir / "requirements.txt").write_text(requirements)
    (deploy_dir / "README.md").write_text(readme)
    (deploy_dir / "Dockerfile").write_text(dockerfile)
    
    print(f"  Created: app.py, requirements.txt, README.md, Dockerfile")


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
            commit_message="Deploy council heartbeat service v1.0",
        )
    
    space_url = f"https://huggingface.co/spaces/{repo_id}"
    print(f"\n✅ Deployed successfully!")
    print(f"   URL: {space_url}")
    print(f"   Health: {space_url.replace('huggingface.co/spaces', repo_id.split('/')[0] + '.hf.space')}")
    print(f"\n   Note: It may take 1-2 minutes for the space to build and start.")
    
    return {"repo_id": repo_id, "url": space_url, "status": "deployed"}


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
    
    # Save deployment record
    record_file = PROJECT_ROOT / "evolution" / "hf_deployment.json"
    record_file.parent.mkdir(parents=True, exist_ok=True)
    import json
    with open(record_file, "w") as f:
        json.dump({
            **result,
            "deployed_at": datetime.now(timezone.utc).isoformat() if 'datetime' in dir() else "now",
            "deployed_by": "operator",
        }, f, indent=2)
    print(f"\n  Deployment record saved to: {record_file}")


if __name__ == "__main__":
    from datetime import datetime, timezone
    main()
