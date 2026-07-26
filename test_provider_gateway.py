"""
Test all configured LLM providers to verify which work.
Tests each provider with a simple request and logs results.
"""
import os
import sys
import asyncio
import yaml
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def load_providers():
    """Load provider configuration from YAML."""
    with open('providers.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config.get('providers', [])

async def test_provider(provider, client):
    """Test a single provider with a simple request."""
    name = provider['name']
    api_key_env = provider['api_key_env']
    api_key = os.getenv(api_key_env)
    
    if not api_key:
        return {
            'provider': name,
            'status': 'SKIPPED',
            'reason': f'No API key ({api_key_env})',
            'response_time': 0
        }
    
    base_url = provider['base_url']
    model = provider['default_model']
    path = provider.get('path', 'chat/completions')
    
    # Handle special URL patterns
    if '{account_id}' in base_url:
        account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID', '')
        if not account_id:
            return {
                'provider': name,
                'status': 'SKIPPED',
                'reason': 'Missing CLOUDFLARE_ACCOUNT_ID',
                'response_time': 0
            }
        base_url = base_url.replace('{account_id}', account_id)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say 'test successful' in one word."}],
        "temperature": 0.1,
        "max_tokens": 10
    }
    
    # Different providers use different paths
    if path == 'chat/completions':
        url = f"{base_url}/chat/completions"
    elif path == 'v1/openai/chat/completions':
        url = f"{base_url}/v1/openai/chat/completions"
    elif path == 'models':
        url = f"{base_url}/{model}"
        payload.pop('model', None)
    else:
        url = f"{base_url}/{path}"
    
    start_time = datetime.utcnow()
    try:
        response = await client.post(url, headers=headers, json=payload, timeout=30)
        response_time = (datetime.utcnow() - start_time).total_seconds()
        
        if response.status_code == 200:
            return {
                'provider': name,
                'status': 'SUCCESS',
                'model': model,
                'response_time': response_time,
                'status_code': response.status_code
            }
        elif response.status_code == 429:
            return {
                'provider': name,
                'status': 'RATE_LIMITED',
                'reason': f'HTTP {response.status_code}',
                'response_time': response_time
            }
        else:
            error_text = response.text[:200]
            return {
                'provider': name,
                'status': 'FAILED',
                'reason': f'HTTP {response.status_code}: {error_text}',
                'response_time': response_time
            }
    except httpx.TimeoutException:
        response_time = (datetime.utcnow() - start_time).total_seconds()
        return {
            'provider': name,
            'status': 'TIMEOUT',
            'reason': 'Request timed out after 30s',
            'response_time': response_time
        }
    except Exception as e:
        response_time = (datetime.utcnow() - start_time).total_seconds()
        return {
            'provider': name,
            'status': 'ERROR',
            'reason': str(e)[:200],
            'response_time': response_time
        }

async def test_local_ollama(client):
    """Test local Ollama if available."""
    base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    
    try:
        # Check if Ollama is running
        response = await client.get(f"{base_url}/api/tags", timeout=5)
        if response.status_code != 200:
            return {
                'provider': 'local-ollama',
                'status': 'FAILED',
                'reason': f'Ollama not responding (HTTP {response.status_code})',
                'response_time': 0
            }
        
        # Try a simple request
        payload = {
            "model": "qwen3.5:4b",
            "messages": [{"role": "user", "content": "Say 'test' in one word."}],
            "stream": False
        }
        
        start_time = datetime.utcnow()
        response = await client.post(f"{base_url}/api/chat", json=payload, timeout=30)
        response_time = (datetime.utcnow() - start_time).total_seconds()
        
        if response.status_code == 200:
            return {
                'provider': 'local-ollama',
                'status': 'SUCCESS',
                'model': 'qwen3.5:4b',
                'response_time': response_time
            }
        else:
            return {
                'provider': 'local-ollama',
                'status': 'FAILED',
                'reason': f'HTTP {response.status_code}',
                'response_time': response_time
            }
    except Exception as e:
        return {
            'provider': 'local-ollama',
            'status': 'FAILED',
            'reason': f'Ollama not running: {str(e)[:100]}',
            'response_time': 0
        }

async def main():
    print("=" * 80)
    print("LLM PROVIDER GATEWAY TEST")
    print("=" * 80)
    print(f"Test started: {datetime.utcnow().isoformat()}")
    print()
    
    providers = load_providers()
    results = []
    
    async with httpx.AsyncClient() as client:
        # Test cloud providers
        print(f"Testing {len(providers)} cloud providers...")
        print()
        
        for provider in providers:
            print(f"  Testing {provider['name']}...", end=' ', flush=True)
            result = await test_provider(provider, client)
            results.append(result)
            
            status_icon = {
                'SUCCESS': '[OK]',
                'FAILED': '[FAIL]',
                'SKIPPED': '[SKIP]',
                'RATE_LIMITED': '[429]',
                'TIMEOUT': '[TIMEOUT]',
                'ERROR': '[ERROR]'
            }.get(result['status'], '[?]')
            
            print(f"{status_icon} {result['status']}")
            if result['status'] != 'SUCCESS':
                print(f"    Reason: {result.get('reason', 'N/A')}")
        
        # Test local Ollama
        print()
        print("Testing local Ollama...")
        ollama_result = await test_local_ollama(client)
        results.append(ollama_result)
        
        status_icon = {
            'SUCCESS': '[OK]',
            'FAILED': '[FAIL]',
            'SKIPPED': '[SKIP]'
        }.get(ollama_result['status'], '[?]')
        
        print(f"  {status_icon} {ollama_result['status']}")
        if ollama_result['status'] != 'SUCCESS':
            print(f"    Reason: {ollama_result.get('reason', 'N/A')}")
    
    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    successful = [r for r in results if r['status'] == 'SUCCESS']
    failed = [r for r in results if r['status'] == 'FAILED']
    skipped = [r for r in results if r['status'] == 'SKIPPED']
    rate_limited = [r for r in results if r['status'] == 'RATE_LIMITED']
    timeout = [r for r in results if r['status'] == 'TIMEOUT']
    error = [r for r in results if r['status'] == 'ERROR']
    
    print(f"Total providers: {len(results)}")
    print(f"  [OK] Successful: {len(successful)}")
    print(f"  [FAIL] Failed: {len(failed)}")
    print(f"  [SKIP] Skipped: {len(skipped)}")
    print(f"  [429] Rate Limited: {len(rate_limited)}")
    print(f"  [TIMEOUT] Timeout: {len(timeout)}")
    print(f"  [ERROR] Error: {len(error)}")
    
    if successful:
        print()
        print("Working providers:")
        for r in successful:
            print(f"  [OK] {r['provider']} ({r.get('model', 'N/A')}) - {r['response_time']:.2f}s")
    
    if failed or error:
        print()
        print("Failed providers:")
        for r in failed + error:
            print(f"  [FAIL] {r['provider']}: {r.get('reason', 'Unknown error')}")
    
    # Save results to file
    with open('provider_test_results.md', 'w') as f:
        f.write("# LLM Provider Gateway Test Results\n\n")
        f.write(f"**Test Date:** {datetime.utcnow().isoformat()}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- Total providers: {len(results)}\n")
        f.write(f"- Successful: {len(successful)}\n")
        f.write(f"- Failed: {len(failed)}\n")
        f.write(f"- Skipped: {len(skipped)}\n")
        f.write(f"- Rate Limited: {len(rate_limited)}\n")
        f.write(f"- Timeout: {len(timeout)}\n")
        f.write(f"- Error: {len(error)}\n\n")
        
        if successful:
            f.write(f"## Working Providers\n\n")
            for r in successful:
                f.write(f"- **{r['provider']}** ({r.get('model', 'N/A')}) - {r['response_time']:.2f}s\n")
            f.write("\n")
        
        if failed or error:
            f.write(f"## Failed Providers\n\n")
            for r in failed + error:
                f.write(f"- **{r['provider']}**: {r.get('reason', 'Unknown error')}\n")
            f.write("\n")
        
        if skipped:
            f.write(f"## Skipped Providers (No API Key)\n\n")
            for r in skipped:
                f.write(f"- {r['provider']}: {r.get('reason', 'No API key')}\n")
            f.write("\n")
        
        f.write(f"## Detailed Results\n\n")
        for r in results:
            f.write(f"### {r['provider']}\n")
            f.write(f"- Status: {r['status']}\n")
            if 'model' in r:
                f.write(f"- Model: {r['model']}\n")
            if 'response_time' in r:
                f.write(f"- Response Time: {r['response_time']:.2f}s\n")
            if 'reason' in r:
                f.write(f"- Reason: {r['reason']}\n")
            f.write("\n")
    
    print()
    print("Results saved to: provider_test_results.md")
    print()
    
    # Return exit code based on results
    if len(successful) > 0:
        print("[OK] At least one provider is working - system can operate")
        return 0
    else:
        print("[FAIL] No providers are working - system cannot operate")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
