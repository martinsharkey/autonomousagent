# Ollama Docker Setup Script
# Run this after Docker Desktop is installed

Write-Host "=== Ollama Docker Setup ===" -ForegroundColor Cyan

# Check if Docker is installed
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker is not installed or not in PATH" -ForegroundColor Red
        Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "✅ Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not installed" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    exit 1
}

# Check if Docker is running
$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker daemon is not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Docker daemon is running" -ForegroundColor Green

# Start Ollama container
Write-Host "`n=== Starting Ollama Container ===" -ForegroundColor Cyan
docker-compose -f docker-compose.ollama.yml up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start Ollama container" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Ollama container started" -ForegroundColor Green

# Wait for Ollama to initialize
Write-Host "`nWaiting for Ollama to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Check if Ollama is responding
$maxRetries = 10
$retryCount = 0
$ollamaReady = $false

while ($retryCount -lt $maxRetries -and -not $ollamaReady) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $ollamaReady = $true
            Write-Host "✅ Ollama is responding" -ForegroundColor Green
        }
    } catch {
        $retryCount++
        Write-Host "  Attempt $retryCount/$maxRetries - waiting..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }
}

if (-not $ollamaReady) {
    Write-Host "❌ Ollama is not responding after $maxRetries attempts" -ForegroundColor Red
    Write-Host "Check logs: docker logs council-ollama" -ForegroundColor Yellow
    exit 1
}

# Pull required models
Write-Host "`n=== Pulling Required Models ===" -ForegroundColor Cyan

$models = @(
    @{Name="qwen3.5:4b"; Agent="Autobot (orchestrator)"},
    @{Name="phi4-mini"; Agent="Alpha (evaluator)"},
    @{Name="deepseek-coder:1.3b"; Agent="Beta (worker)"}
)

foreach ($model in $models) {
    Write-Host "`nPulling $($model.Name) for $($model.Agent)..." -ForegroundColor Yellow
    docker exec -it council-ollama ollama pull $model.Name
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Failed to pull $($model.Name)" -ForegroundColor Yellow
    } else {
        Write-Host "✅ $($model.Name) pulled successfully" -ForegroundColor Green
    }
}

# List installed models
Write-Host "`n=== Installed Models ===" -ForegroundColor Cyan
docker exec -it council-ollama ollama list

# Update .env file
Write-Host "`n=== Updating .env Configuration ===" -ForegroundColor Cyan

$envFile = ".env"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile
    
    # Check if OLLAMA_BASE_URL is set
    if (-not ($envContent -match "OLLAMA_BASE_URL")) {
        Add-Content $envFile "`nOLLAMA_BASE_URL=http://localhost:11434"
        Write-Host "✅ Added OLLAMA_BASE_URL to .env" -ForegroundColor Green
    } else {
        Write-Host "✅ OLLAMA_BASE_URL already configured" -ForegroundColor Green
    }
} else {
    Write-Host "⚠️  .env file not found" -ForegroundColor Yellow
}

# Final status
Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Ollama is running at: http://localhost:11434" -ForegroundColor Green
Write-Host "Container name: council-ollama" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Start the council daemon: python council_daemon.py" -ForegroundColor White
Write-Host "2. Test Telegram: /status" -ForegroundColor White
Write-Host "3. Create a goal: /goal Write a hello world script" -ForegroundColor White
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  View logs: docker logs council-ollama" -ForegroundColor White
Write-Host "  Stop Ollama: docker-compose -f docker-compose.ollama.yml down" -ForegroundColor White
Write-Host "  Restart Ollama: docker-compose -f docker-compose.ollama.yml restart" -ForegroundColor White
