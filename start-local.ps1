# start-local.ps1 - Safe mode demo launcher for Autonomous 3-Agent Council
# This script runs a demonstration of the state machine without executing any generated code

Write-Host "=== Autonomous Council - Safe Mode Demo ===" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path ".\venv")) {
    Write-Host "✗ Virtual environment not found." -ForegroundColor Red
    Write-Host "Please run setup.ps1 first:" -ForegroundColor Yellow
    Write-Host "  .\setup.ps1" -ForegroundColor White
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
try {
    & ".\venv\Scripts\Activate.ps1"
    Write-Host "✓ Virtual environment activated" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to activate virtual environment" -ForegroundColor Red
    exit 1
}

# Check if required modules can be imported
Write-Host "Verifying dependencies..." -ForegroundColor Yellow
try {
    python -c "import langgraph; import langchain; import pydantic" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Missing dependencies"
    }
    Write-Host "✓ All dependencies verified" -ForegroundColor Green
} catch {
    Write-Host "✗ Dependencies not installed correctly" -ForegroundColor Red
    Write-Host "Please run: pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Run the safe demo
Write-Host ""
Write-Host "Starting safe mode demonstration..." -ForegroundColor Yellow
Write-Host "This demo shows state transitions without code execution." -ForegroundColor Yellow
Write-Host ""

try {
    python -c @"
import sys
from core.state import AgentState
from langchain_core.messages import HumanMessage, AIMessage

print('Initializing state machine...')
print('')

# Create initial state
initial_state = {
    'messages': [HumanMessage(content='Write a web scraper')],
    'loop_count': 0,
    'recent_tool_invocations': [],
    'completed_nodes': [],
    'codebase_hash': ''
}

print('[Autobot] Analyzing task: Write a web scraper')
print('  → Decision: Delegate to Beta Worker')
print('')

# Simulate state transition to Beta
state_after_autobot = {
    'messages': [
        HumanMessage(content='Write a web scraper'),
        AIMessage(content='EXECUTE_CODE: Create Python web scraper using requests')
    ],
    'loop_count': 1,
    'recent_tool_invocations': [],
    'completed_nodes': ['autobot'],
    'codebase_hash': ''
}

print('[Beta] Generating code structure')
print('  → Decision: Code ready for review')
print('')

# Simulate state transition to Alpha
state_after_beta = {
    'messages': [
        HumanMessage(content='Write a web scraper'),
        AIMessage(content='EXECUTE_CODE: Create Python web scraper using requests'),
        AIMessage(content='REVIEW_REQUIRED: Code generated, awaiting evaluation')
    ],
    'loop_count': 2,
    'recent_tool_invocations': [],
    'completed_nodes': ['autobot', 'beta_worker'],
    'codebase_hash': 'abc123'
}

print('[Alpha] Reviewing code quality')
print('  → Decision: Code passes review')
print('')

# Simulate state transition back to Autobot
state_after_alpha = {
    'messages': [
        HumanMessage(content='Write a web scraper'),
        AIMessage(content='EXECUTE_CODE: Create Python web scraper using requests'),
        AIMessage(content='REVIEW_REQUIRED: Code generated, awaiting evaluation'),
        AIMessage(content='CONSENSUS_REACHED: Code approved by evaluator')
    ],
    'loop_count': 3,
    'recent_tool_invocations': [],
    'completed_nodes': ['autobot', 'beta_worker', 'alpha_evaluator'],
    'codebase_hash': 'def456'
}

print('[Autobot] Consensus reached')
print('')
print('=== Demo Complete ===')
print(f'Loop count: {state_after_alpha[\"loop_count\"]}')
print(f'Completed nodes: {state_after_alpha[\"completed_nodes\"]}')
print('')
print('This demo showed the state machine flow:')
print('  Autobot → Beta Worker → Alpha Evaluator → Autobot (consensus)')
print('')
print('In full mode, the system would:')
print('  1. Generate actual code using local LLMs')
print('  2. Execute code in a MicroVM sandbox')
print('  3. Apply 4-layer governance (LGA)')
print('  4. Maintain immutable audit logs')
"@

    if ($LASTEXITCODE -ne 0) {
        throw "Demo execution failed"
    }
} catch {
    Write-Host "✗ Demo execution failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Demo Finished ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "To run the full system with local LLMs:" -ForegroundColor Yellow
Write-Host "1. Install Ollama from https://ollama.ai/download" -ForegroundColor White
Write-Host "2. Pull required models:" -ForegroundColor White
Write-Host "   ollama pull qwen3.5:4b" -ForegroundColor Cyan
Write-Host "   ollama pull phi4-mini" -ForegroundColor Cyan
Write-Host "   ollama pull deepseek-coder:1.3b" -ForegroundColor Cyan
Write-Host "3. Run the full system:" -ForegroundColor White
Write-Host "   python main.py" -ForegroundColor Cyan
Write-Host ""
