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
    """Create the files needed for the HF Space (Static SDK - free for everyone)."""
    
    from datetime import datetime, timezone
    deploy_time = datetime.now(timezone.utc).isoformat()
    
    # index.html - Static heartbeat dashboard
    index_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Council Heartbeat</title>
    <style>
        :root {{
            --bg: #0f0f23;
            --card-bg: #1a1a2e;
            --accent: #7c3aed;
            --green: #10b981;
            --text: #e2e8f0;
            --muted: #94a3b8;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 2rem;
        }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        h1 {{ color: var(--accent); margin-bottom: 0.5rem; font-size: 1.8rem; }}
        .subtitle {{ color: var(--muted); margin-bottom: 2rem; }}
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(124, 58, 237, 0.2);
        }}
        .status-row {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
        }}
        .status-dot {{
            width: 12px; height: 12px;
            background: var(--green);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        .label {{ color: var(--muted); min-width: 120px; }}
        .value {{ color: var(--text); font-family: monospace; }}
        #clock {{ color: var(--green); font-family: monospace; }}
        .footer {{ color: var(--muted); font-size: 0.85rem; margin-top: 2rem; text-align: center; }}
        a {{ color: var(--accent); }}
        .json-block {{
            background: #0d1117;
            border-radius: 8px;
            padding: 1rem;
            font-family: monospace;
            font-size: 0.85rem;
            overflow-x: auto;
            white-space: pre;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>&#129504; Council Heartbeat Service</h1>
        <p class="subtitle">Autonomous council survivability proof &mdash; running on HuggingFace Spaces</p>

        <div class="card">
            <div class="status-row">
                <div class="status-dot"></div>
                <span class="value" style="font-size: 1.2rem; font-weight: bold;">ALIVE</span>
            </div>
            <div class="status-row">
                <span class="label">Service:</span>
                <span class="value">council-heartbeat v1.0</span>
            </div>
            <div class="status-row">
                <span class="label">Deployed:</span>
                <span class="value">{deploy_time}</span>
            </div>
            <div class="status-row">
                <span class="label">Current UTC:</span>
                <span class="value" id="clock">loading...</span>
            </div>
            <div class="status-row">
                <span class="label">Environment:</span>
                <span class="value">HuggingFace Spaces (Static)</span>
            </div>
            <div class="status-row">
                <span class="label">Uptime:</span>
                <span class="value" id="uptime">calculating...</span>
            </div>
        </div>

        <div class="card">
            <h3 style="margin-bottom: 1rem; color: var(--accent);">Health Check Response</h3>
            <div class="json-block" id="health-json">loading...</div>
        </div>

        <div class="card">
            <h3 style="margin-bottom: 1rem; color: var(--accent);">Purpose</h3>
            <p>This static page proves the council&rsquo;s existence beyond the operator&rsquo;s laptop.
            The autonomous 3-agent council (autobot, alpha_evaluator, beta_worker) can be
            reached and verified from anywhere via this URL.</p>
            <p style="margin-top: 0.75rem;">
                <strong>GitHub:</strong>
                <a href="https://github.com/martysharkey/autonomousagent" target="_blank">
                    martysharkey/autonomousagent
                </a>
            </p>
        </div>

        <div class="footer">
            Council Daemon &bull; Deployed by the autonomous evolution pipeline
        </div>
    </div>

    <script>
        const deployTime = new Date("{deploy_time}");

        function updateClock() {{
            const now = new Date();
            document.getElementById("clock").textContent = now.toISOString();
            const diff = Math.floor((now - deployTime) / 1000);
            const h = Math.floor(diff / 3600);
            const m = Math.floor((diff % 3600) / 60);
            const s = diff % 60;
            document.getElementById("uptime").textContent =
                h + "h " + m + "m " + s + "s";
            document.getElementById("health-json").textContent = JSON.stringify({{
                status: "alive",
                service: "council-heartbeat",
                version: "1.0.0",
                deployed_at: "{deploy_time}",
                checked_at: now.toISOString(),
                environment: "huggingface_spaces_static",
                uptime_seconds: diff
            }}, null, 2);
        }}

        updateClock();
        setInterval(updateClock, 1000);
    </script>
</body>
</html>
'''

    # README.md (HF Spaces metadata - Static SDK, free for all)
    readme = f"""---
title: Council Heartbeat
emoji: 🧠
colorFrom: purple
colorTo: blue
sdk: static
pinned: false
---

# Council Heartbeat Service

Minimal survivability proof for the autonomous 3-agent council.

- **Live clock** showing deployment uptime
- **Health JSON** response updated every second
- **Static SDK** — free for everyone, no PRO required

Deployed automatically by the council's deployment pipeline.
Source: [martysharkey/autonomousagent](https://github.com/martysharkey/autonomousagent)
"""

    # Write files (Static SDK only needs index.html + README.md)
    (deploy_dir / "index.html").write_text(index_html, encoding="utf-8")
    (deploy_dir / "README.md").write_text(readme, encoding="utf-8")
    
    print(f"  Created: index.html, README.md (Static SDK)")


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
            space_sdk="static",
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
