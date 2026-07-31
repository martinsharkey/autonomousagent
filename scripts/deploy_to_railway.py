#!/usr/bin/env python3
"""Deploy council daemon to Railway (free tier: $5/month credit, persistent Docker).

Railway is the best free option for running the council daemon as a persistent process:
- Docker containers run 24/7
- Free $5/month trial credit (enough for 1 lightweight service)
- Auto-deploy from GitHub repo
- Environment variables for secrets
- No credit card required for trial

Prerequisites:
    1. Sign up at https://railway.app (GitHub OAuth)
    2. Install Railway CLI: npm i -g @railway/cli
    3. Login: railway login
    4. Link project: railway link (or this script creates one)

Usage:
    python scripts/deploy_to_railway.py [--project-name NAME]

Alternative free platforms (if Railway credit exhausted):
    - Render: Free web service (sleeps after 15min, use /health endpoint + cron ping)
    - Koyeb: 1 free nano instance, always-on
    - Fly.io: 3 free shared VMs
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_railway_cli() -> bool:
    """Check if Railway CLI is installed and authenticated."""
    try:
        result = subprocess.run(
            ["railway", "version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"  ✓ Railway CLI: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    return False


def check_railway_auth() -> bool:
    """Check if Railway CLI is authenticated."""
    try:
        result = subprocess.run(
            ["railway", "whoami"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"  ✓ Authenticated as: {result.stdout.strip()}")
            return True
    except Exception:
        pass
    return False


def create_dockerfile():
    """Create a Dockerfile for the council daemon."""
    dockerfile = PROJECT_ROOT / "Dockerfile.daemon"
    
    content = '''# Council Daemon - Railway Deployment
FROM python:3.11-slim

WORKDIR /app

# Install git (needed for auto-commits and sync)
RUN apt-get update && apt-get install -y --no-install-recommends git && \\
    rm -rf /var/lib/apt/lists/*

# Configure git identity
RUN git config --global user.name "Council Daemon" && \\
    git config --global user.email "council-daemon@autonomousagent.local"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . .

# Create necessary directories
RUN mkdir -p goals evolution/mutations checkpoints logs

# Health check endpoint (the daemon exposes nothing by default,
# but Railway needs a PORT listener to stay alive)
ENV PORT=8080

# Start the daemon with a minimal health server
CMD ["python", "-u", "scripts/railway_entrypoint.py"]
'''
    
    dockerfile.write_text(content)
    print(f"  Created: Dockerfile.daemon")
    return dockerfile


def create_entrypoint():
    """Create the Railway entrypoint that runs daemon + health server."""
    entrypoint = PROJECT_ROOT / "scripts" / "railway_entrypoint.py"
    
    content = '''#!/usr/bin/env python3
"""Railway entrypoint: runs council daemon + minimal health HTTP server.

Railway requires a process listening on $PORT to keep the service alive.
This script runs both the daemon and a tiny health endpoint concurrently.
"""

import os
import sys
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Inject vault secrets before anything else
try:
    from core.secrets_vault import get_vault
    vault = get_vault()
    if vault.is_unlocked:
        injected = vault.inject_into_environment()
        print(f"[RAILWAY] Vault unlocked: injected {injected} secrets")
except Exception as e:
    print(f"[RAILWAY] Vault not available: {e}")


async def health_server():
    """Minimal HTTP health server on $PORT."""
    from aiohttp import web
    
    start_time = datetime.now(timezone.utc)
    
    async def health_handler(request):
        now = datetime.now(timezone.utc)
        uptime = (now - start_time).total_seconds()
        
        # Try to get daemon status
        status = "unknown"
        try:
            pid_file = Path("council_daemon.pid")
            if pid_file.exists():
                status = "running"
            else:
                status = "starting"
        except Exception:
            pass
        
        return web.json_response({
            "status": "alive",
            "daemon_status": status,
            "service": "council-daemon",
            "environment": "railway",
            "started_at": start_time.isoformat(),
            "uptime_seconds": int(uptime),
            "checked_at": now.isoformat(),
        })
    
    async def root_handler(request):
        return web.Response(
            text="Council Daemon - Railway Deployment\\n"
                 "GET /health for status\\n",
            content_type="text/plain"
        )
    
    app = web.Application()
    app.router.add_get("/", root_handler)
    app.router.add_get("/health", health_handler)
    
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[RAILWAY] Health server listening on port {port}")
    
    # Keep running forever
    while True:
        await asyncio.sleep(3600)


async def run_daemon():
    """Start the council daemon."""
    # Give health server a moment to start first
    await asyncio.sleep(2)
    
    print("[RAILWAY] Starting council daemon...")
    
    try:
        from council_daemon import CouncilDaemon
        
        cycle_interval = int(os.environ.get("COUNCIL_CYCLE_INTERVAL", "120"))
        autonomy_level = os.environ.get("COUNCIL_AUTONOMY_LEVEL", "limited")
        
        daemon = CouncilDaemon(
            cycle_interval=cycle_interval,
            autonomy_level=autonomy_level
        )
        await daemon.start()
    except Exception as e:
        print(f"[RAILWAY] Daemon error: {e}")
        import traceback
        traceback.print_exc()
        # Don't crash - keep health server alive so Railway doesn't restart
        while True:
            await asyncio.sleep(60)


async def main():
    """Run health server and daemon concurrently."""
    await asyncio.gather(
        health_server(),
        run_daemon(),
    )


if __name__ == "__main__":
    print(f"[RAILWAY] Council daemon starting at {datetime.now(timezone.utc).isoformat()}")
    asyncio.run(main())
'''
    
    entrypoint.write_text(content)
    print(f"  Created: scripts/railway_entrypoint.py")
    return entrypoint


def create_railway_config():
    """Create railway.toml configuration."""
    config = PROJECT_ROOT / "railway.toml"
    
    content = '''[build]
dockerfilePath = "Dockerfile.daemon"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 5
'''
    
    config.write_text(content)
    print(f"  Created: railway.toml")
    return config


def get_required_env_vars() -> dict:
    """Get environment variables needed for Railway deployment."""
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    
    # Try vault
    try:
        from core.secrets_vault import get_vault
        vault = get_vault()
        if vault.is_unlocked:
            vault.inject_into_environment()
    except Exception:
        pass
    
    env_vars = {}
    
    # Required
    for key in ["OPENROUTER_API_KEY", "GROQ_API_KEY", "GOOGLE_API_KEY"]:
        val = os.getenv(key)
        if val:
            env_vars[key] = val
    
    # Optional but useful
    for key in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GITHUB_TOKEN",
                "COUNCIL_MASTER_KEY", "HF_API_KEY"]:
        val = os.getenv(key)
        if val:
            env_vars[key] = val
    
    # Deployment-specific
    env_vars["COUNCIL_CYCLE_INTERVAL"] = os.getenv("COUNCIL_CYCLE_INTERVAL", "120")
    env_vars["COUNCIL_AUTONOMY_LEVEL"] = os.getenv("COUNCIL_AUTONOMY_LEVEL", "limited")
    
    return env_vars


def deploy_via_cli(project_name: str):
    """Deploy to Railway using the CLI."""
    print(f"\n🚀 Deploying to Railway...")
    
    # Check if we're in a Railway project
    result = subprocess.run(
        ["railway", "status"],
        capture_output=True, text=True, timeout=10,
        cwd=str(PROJECT_ROOT)
    )
    
    if result.returncode != 0:
        # Need to create/link a project
        print(f"  Creating Railway project: {project_name}")
        result = subprocess.run(
            ["railway", "init", "--name", project_name],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT)
        )
        if result.returncode != 0:
            print(f"  ERROR: Could not create project: {result.stderr}")
            print(f"  Try manually: cd {PROJECT_ROOT} && railway init")
            return False
    
    # Set environment variables
    env_vars = get_required_env_vars()
    if env_vars:
        print(f"  Setting {len(env_vars)} environment variables...")
        for key, val in env_vars.items():
            subprocess.run(
                ["railway", "variables", "set", f"{key}={val}"],
                capture_output=True, text=True, timeout=10,
                cwd=str(PROJECT_ROOT)
            )
    
    # Deploy
    print(f"  Deploying (this may take 2-5 minutes)...")
    result = subprocess.run(
        ["railway", "up", "--detach"],
        capture_output=True, text=True, timeout=300,
        cwd=str(PROJECT_ROOT)
    )
    
    if result.returncode == 0:
        print(f"\n✅ Deployed successfully!")
        print(f"   {result.stdout.strip()}")
        
        # Get the deployment URL
        url_result = subprocess.run(
            ["railway", "domain"],
            capture_output=True, text=True, timeout=10,
            cwd=str(PROJECT_ROOT)
        )
        if url_result.returncode == 0 and url_result.stdout.strip():
            url = url_result.stdout.strip()
            print(f"   URL: https://{url}")
            print(f"   Health: https://{url}/health")
        
        return True
    else:
        print(f"  ERROR: Deploy failed: {result.stderr}")
        return False


def print_manual_instructions(project_name: str):
    """Print manual deployment instructions."""
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  MANUAL RAILWAY DEPLOYMENT INSTRUCTIONS                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. Install Railway CLI:                                     ║
║     npm i -g @railway/cli                                    ║
║                                                              ║
║  2. Login:                                                   ║
║     railway login                                            ║
║                                                              ║
║  3. Initialize project (from repo root):                     ║
║     cd {str(PROJECT_ROOT)}
║     railway init --name {project_name}
║                                                              ║
║  4. Set secrets:                                             ║
║     railway variables set OPENROUTER_API_KEY=xxx             ║
║     railway variables set GROQ_API_KEY=xxx                   ║
║     railway variables set COUNCIL_MASTER_KEY=xxx             ║
║     railway variables set TELEGRAM_BOT_TOKEN=xxx             ║
║     railway variables set TELEGRAM_CHAT_ID=xxx               ║
║                                                              ║
║  5. Deploy:                                                  ║
║     railway up --detach                                      ║
║                                                              ║
║  6. Get URL:                                                 ║
║     railway domain                                           ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  ALTERNATIVE: Deploy via Railway Dashboard                   ║
║  https://railway.app/new → Deploy from GitHub repo           ║
║  Select: martinsharkey/autonomousagent                        ║
║  Set Dockerfile path: Dockerfile.daemon                      ║
╚══════════════════════════════════════════════════════════════╝

Alternative Free Platforms (if Railway trial expires):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Render (render.com)     — Free web service, sleeps after 15min
                              Use with cron-job.org ping to /health every 14min
  • Koyeb (koyeb.com)      — 1 free nano instance (256MB), always-on
                              Deploy from GitHub, Docker support
  • Fly.io (fly.io)        — 3 free shared VMs (256MB each)
                              fly launch → fly deploy
""")


def main():
    parser = argparse.ArgumentParser(description="Deploy council daemon to Railway")
    parser.add_argument("--project-name", default="council-daemon",
                        help="Railway project name")
    parser.add_argument("--setup-only", action="store_true",
                        help="Only create deployment files, don't deploy")
    args = parser.parse_args()
    
    print("🧠 Council Daemon → Railway Deployer")
    print("=" * 50)
    
    # Create deployment files
    print("\n📦 Creating deployment files...")
    create_dockerfile()
    create_entrypoint()
    create_railway_config()
    
    if args.setup_only:
        print("\n✓ Deployment files created. Run without --setup-only to deploy.")
        print_manual_instructions(args.project_name)
        return
    
    # Check Railway CLI
    print("\n🔍 Checking Railway CLI...")
    if not check_railway_cli():
        print("  ✗ Railway CLI not installed.")
        print("  Install: npm i -g @railway/cli")
        print_manual_instructions(args.project_name)
        return
    
    if not check_railway_auth():
        print("  ✗ Not authenticated. Run: railway login")
        print_manual_instructions(args.project_name)
        return
    
    # Deploy
    success = deploy_via_cli(args.project_name)
    
    if success:
        # Save deployment record
        record = {
            "platform": "railway",
            "project_name": args.project_name,
            "deployed_at": datetime.now(timezone.utc).isoformat(),
            "dockerfile": "Dockerfile.daemon",
            "entrypoint": "scripts/railway_entrypoint.py",
        }
        record_file = PROJECT_ROOT / "evolution" / "railway_deployment.json"
        record_file.parent.mkdir(parents=True, exist_ok=True)
        with open(record_file, "w") as f:
            json.dump(record, f, indent=2)


if __name__ == "__main__":
    main()
