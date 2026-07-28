import asyncio
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from core.agent_loop import get_agent_loop
from core.evolution import get_evolution_engine

async def main():
    loop = get_agent_loop('autobot', 60)
    loop.cycle_count = 19
    loop._last_evolution_cycle = -10
    loop._last_architecture_review = -20
    
    start = datetime.utcnow()
    print(f"[VERIFY] START {start.isoformat()}")
    
    try:
        await loop.run_cycle()
        print("[VERIFY] CYCLE_RUN_COMPLETED")
    except Exception as e:
        print(f"[VERIFY] CYCLE_ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    end = datetime.utcnow()
    print(f"[VERIFY] END {end.isoformat()}")
    print(f"[VERIFY] DURATION {(end-start).total_seconds():.2f}s")
    
    engine = get_evolution_engine()
    recent = [m for m in engine.mutations.values() if m.agent_name == 'autobot']
    recent_sorted = sorted(recent, key=lambda m: m.timestamp, reverse=True)[:5]
    for m in recent_sorted:
        print(f"[VERIFY] MUTATION {m.mutation_id[:12]} status={m.status.value} ts={m.timestamp}")

asyncio.run(main())
