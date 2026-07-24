# setup.ps1 - Windows setup script for Autonomous 3-Agent Council
# This script creates a virtual environment and installs all dependencies

Write-Host "=== Autonomous Council Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Found $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Please install Python 3.10+ from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# Check if virtual environment already exists
if (Test-Path ".\venv") {
    Write-Host "Virtual environment already exists." -ForegroundColor Yellow
    $overwrite = Read-Host "Do you want to recreate it? (y/n)"
    if ($overwrite -eq "y") {
        Write-Host "Removing existing virtual environment..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force ".\venv"
    } else {
        Write-Host "Using existing virtual environment." -ForegroundColor Green
        Write-Host ""
        Write-Host "To activate the environment, run:" -ForegroundColor Cyan
        Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
        Write-Host ""
        Write-Host "Then install dependencies with:" -ForegroundColor Cyan
        Write-Host "  pip install -r requirements.txt" -ForegroundColor White
        exit 0
    }
}

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
try {
    python -m venv venv
    Write-Host "✓ Virtual environment created successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to create virtual environment" -ForegroundColor Red
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
try {
    & ".\venv\Scripts\Activate.ps1"
    Write-Host "✓ Virtual environment activated" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to activate virtual environment" -ForegroundColor Red
    Write-Host "You may need to set execution policy:" -ForegroundColor Yellow
    Write-Host "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor White
    exit 1
}

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
try {
    python -m pip install --upgrade pip
    Write-Host "✓ Pip upgraded successfully" -ForegroundColor Green
} catch {
    Write-Host "⚠ Failed to upgrade pip (continuing anyway)" -ForegroundColor Yellow
}

# Install dependencies
Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Yellow
try {
    pip install -r requirements.txt
    Write-Host "✓ All dependencies installed successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Create .env file if it doesn't exist
if (-not (Test-Path ".\.env")) {
    Write-Host "Creating .env file from template..." -ForegroundColor Yellow
    try {
        Copy-Item ".\.env.example" ".\.env"
        Write-Host "✓ .env file created" -ForegroundColor Green
        Write-Host "  Please edit .env to configure your settings" -ForegroundColor Yellow
    } catch {
        Write-Host "⚠ Could not create .env file (template may not exist)" -ForegroundColor Yellow
    }
}

# Create necessary directories
Write-Host "Creating project directories..." -ForegroundColor Yellow
$directories = @("audit_logs", "reasoning_snapshots", "rollback_states")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "✓ Created $dir" -ForegroundColor Green
    }
}

# Final instructions
Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Activate the virtual environment:" -ForegroundColor White
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Install Ollama (if not already installed):" -ForegroundColor White
Write-Host "   Download from https://ollama.ai/download" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Pull required models:" -ForegroundColor White
Write-Host "   ollama pull qwen3.5:4b" -ForegroundColor Cyan
Write-Host "   ollama pull phi4-mini" -ForegroundColor Cyan
Write-Host "   ollama pull deepseek-coder:1.3b" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Run the safe mode demo:" -ForegroundColor White
Write-Host "   .\start-local.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. Or run the full system:" -ForegroundColor White
Write-Host "   python main.py" -ForegroundColor Cyan
Write-Host ""
