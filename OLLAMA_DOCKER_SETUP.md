# Ollama Docker Setup Guide

## Prerequisites

### 1. Create and Activate Virtual Environment

```powershell
# Create venv (if not already created)
python -m venv .venv

# Activate venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

The venv includes:
- `ollama==0.3.0` - Python client for Ollama API
- `langchain-ollama==0.1.0` - LangChain integration
- All other project dependencies

### 2. Install Docker Desktop for Windows

1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop/
2. Run the installer (requires administrator privileges)
3. Restart your computer after installation
4. Start Docker Desktop and wait for it to initialize

### Verify Docker Installation

```powershell
docker --version
docker-compose --version
```

## Setup Ollama with Docker

### Step 1: Start Ollama Container

```powershell
docker-compose -f docker-compose.ollama.yml up -d
```

### Step 2: Wait for Ollama to Initialize

```powershell
# Wait 10-15 seconds for Ollama to start
Start-Sleep -Seconds 15

# Check if Ollama is running
docker logs council-ollama
```

### Step 3: Pull Required Models

```powershell
# Pull Autobot model (orchestrator)
docker exec -it council-ollama ollama pull qwen3.5:4b

# Pull Alpha model (evaluator)
docker exec -it council-ollama ollama pull phi4-mini

# Pull Beta model (worker)
docker exec -it council-ollama ollama pull deepseek-coder:1.3b
```

### Step 4: Verify Models are Installed

```powershell
docker exec -it council-ollama ollama list
```

Expected output:
```
NAME                  ID              SIZE      MODIFIED
qwen3.5:4b           ...             2.3 GB    ...
phi4-mini            ...             1.8 GB    ...
deepseek-coder:1.3b  ...             0.7 GB    ...
```

## Configure Council Daemon

The Python dependencies are installed in the virtual environment (.venv). Update `.env` file to point to Docker Ollama:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MAX_LOADED_MODELS=2
OLLAMA_NUM_PARALLEL=1
OLLAMA_CTX_SIZE=2048
```

## Start Council Daemon

**Always activate the virtual environment first:**

```powershell
# Activate venv
.venv\Scripts\Activate.ps1

# Or use venv Python directly
.venv\Scripts\python.exe council_daemon.py --interval 60 --autonomy limited
```

## Verify Integration

Send Telegram command:
```
/status
```

Expected response:
```
[COUNCIL:DAEMON] 📊 Council Status

Ollama: ✅ Running
Models: ✅ 3/3 loaded
Autonomous cycles: ✅ Active
```

## Troubleshooting

### Ollama Not Responding

```powershell
# Check container status
docker ps | findstr council-ollama

# View logs
docker logs council-ollama

# Restart container
docker-compose -f docker-compose.ollama.yml restart
```

### Models Not Loading

```powershell
# Check available models
docker exec -it council-ollama ollama list

# Pull missing models
docker exec -it council-ollama ollama pull <model-name>
```

### Port Already in Use

```powershell
# Check what's using port 11434
netstat -ano | findstr :11434

# Stop conflicting process or change port in docker-compose.ollama.yml
```

## GPU Support (Optional)

If you have an NVIDIA GPU, uncomment the GPU section in `docker-compose.ollama.yml`:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

Requires:
- NVIDIA GPU drivers
- NVIDIA Container Toolkit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

## Resource Management

### Monitor Resource Usage

```powershell
# Check container stats
docker stats council-ollama

# Check Ollama memory usage
docker exec -it council-ollama ollama ps
```

### Reduce Memory Usage

Edit `docker-compose.ollama.yml`:

```yaml
environment:
  - OLLAMA_MAX_LOADED_MODELS=1  # Load only one model at a time
  - OLLAMA_CTX_SIZE=1024        # Smaller context window
```

## Cleanup

### Stop Ollama

```powershell
docker-compose -f docker-compose.ollama.yml down
```

### Remove Models (Free Disk Space)

```powershell
# Remove specific model
docker exec -it council-ollama ollama rm <model-name>

# Remove all models and volume
docker-compose -f docker-compose.ollama.yml down -v
```

## Portability

This Docker setup ensures:
- ✅ Consistent Ollama version across environments
- ✅ Isolated from host system
- ✅ Easy to deploy on any machine with Docker
- ✅ Models persist in Docker volume
- ✅ Configuration is version-controlled

## Next Steps

After Ollama is running:

1. Test Telegram commands: `/who`, `/status`, `/help`
2. Create a test goal: `/goal Write a hello world script`
3. Monitor autonomous cycles in logs
4. Check Telegram for progress notifications
