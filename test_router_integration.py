"""
Integration test: Verify the LLM router works end-to-end with agents.
Tests that agents can successfully call the cloud router.
"""
import asyncio
import sys
from core.api_router import get_llm_router

async def test_router_integration():
    """Test that the router can successfully route requests."""
    print("=" * 80)
    print("LLM ROUTER INTEGRATION TEST")
    print("=" * 80)
    
    router = get_llm_router()
    
    # Test 1: Check router status
    print("\n[TEST 1] Router Status")
    status = router.get_status()
    print(f"  Backend: {status['backend']}")
    print(f"  Active providers: {status['active_providers']}")
    print(f"  Total providers: {status['total_providers']}")
    print(f"  Local Ollama enabled: {status['local_ollama_enabled']}")
    
    if status['active_providers'] == 0:
        print("  [FAIL] No active providers - router cannot operate")
        return False
    
    print(f"  [OK] Router has {status['active_providers']} active providers")
    
    # Test 2: Make a simple request through the router
    print("\n[TEST 2] Router Request")
    messages = [{"role": "user", "content": "Say 'router test successful' in one word."}]
    
    try:
        response = await router.route_request(messages, temperature=0.1, max_tokens=10)
        
        # Extract content from response
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        if content:
            print(f"  [OK] Router returned response: {content[:50]}")
            print(f"  [OK] Router integration working")
            return True
        else:
            print(f"  [FAIL] Router returned empty response")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Router request failed: {e}")
        return False
    
    finally:
        await router.close()

async def main():
    success = await test_router_integration()
    
    print("\n" + "=" * 80)
    if success:
        print("[OK] ROUTER INTEGRATION TEST PASSED")
        print("Agents can successfully use the cloud router")
        return 0
    else:
        print("[FAIL] ROUTER INTEGRATION TEST FAILED")
        print("Router integration needs fixing")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
