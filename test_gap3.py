import asyncio
import os
import sys
from dotenv import load_dotenv
load_dotenv()
from core.agent_loop import get_agent_loop

loop = get_agent_loop('autobot', 60)
loop.cycle_count = 20
loop._last_evolution_cycle = -10
loop._last_architecture_review = -20

async def test():
    try:
        await loop.run_cycle()
        print('CYCLE_COMPLETED')
        print('last_execution:', loop.last_execution)
    except Exception as e:
        print('CYCLE_ERROR:', e, file=sys.stderr)
        import traceback
        traceback.print_exc()

asyncio.run(test())
