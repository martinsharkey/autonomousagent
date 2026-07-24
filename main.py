import asyncio
import sys
from dotenv import load_dotenv
from core.graph import app
from core.memory import PersistentMemory
from governance.audit_log import log_event
from governance.consensus import ConsensusEngine, StaggeredRollout
from core.model_check import run_preflight, print_report

load_dotenv()

def check_preflight():
    report = run_preflight()
    print_report(report)
    if not report["can_run"]:
        print("Preflight check failed. Cannot start council.")
        sys.exit(1)
    return report

memory = PersistentMemory()
consensus = ConsensusEngine(agents=["autobot", "alpha_evaluator", "beta_worker"])
rollout = StaggeredRollout(consensus)

async def run_council(task: str, skip_preflight: bool = False):
    if not skip_preflight:
        check_preflight()
    
    config = {"configurable": {"thread_id": "council_session_001"}}
    
    initial_state = {
        "messages": [("user", task)],
        "loop_count": 0,
        "completed_nodes": [],
        "recent_tool_invocations": [],
        "codebase_hash": ""
    }
    
    log_event("session_start", "system", "council_initialized", {"task": task})
    
    print("\n" + "="*60)
    print("AUTONOMOUS 3-AGENT COUNCIL - INITIALIZING")
    print("="*60)
    print(f"Task: {task}")
    print(f"Orchestrator: Qwen3.5:4b (Node 1)")
    print(f"Evaluator: Phi-4 Mini (Node 2)")
    print(f"Worker: DeepSeek Coder 1.3B (Node 3)")
    print("="*60 + "\n")
    
    try:
        async for chunk in app.astream(initial_state, config=config, stream_mode="updates"):
            for node_name, state_update in chunk.items():
                print(f"\n[{node_name.upper()}] Update:")
                if "messages" in state_update:
                    for msg in state_update["messages"]:
                        if hasattr(msg, "content"):
                            print(f"  {msg.content[:200]}...")
                
                if "loop_count" in state_update:
                    print(f"  Loop count: {state_update['loop_count']}")
                
                if "completed_nodes" in state_update:
                    print(f"  Completed: {state_update['completed_nodes']}")
                
                log_event("node_execution", node_name, "state_update", state_update)
    
    except Exception as e:
        print(f"\n[ERROR] Council execution failed: {e}")
        log_event("error", "system", "council_failed", {"error": str(e)})
    
    print("\n" + "="*60)
    print("COUNCIL SESSION COMPLETE")
    print("="*60)
    
    memory.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Autonomous 3-Agent Council")
    parser.add_argument("--task", type=str, help="Task for the council")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip model/RAM preflight check")
    parser.add_argument("--safe-mode", action="store_true", help="Run in safe mode (no code execution)")
    parser.add_argument("--mock-llms", action="store_true", help="Use mocked LLM responses")
    args = parser.parse_args()
    
    task = args.task
    if not task:
        task = input("Enter task for the council: ").strip()
    if not task:
        task = "Initialize the council and write a web scraper."
    
    asyncio.run(run_council(task, skip_preflight=args.skip_preflight))

if __name__ == "__main__":
    main()
