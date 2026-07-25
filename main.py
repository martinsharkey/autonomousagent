import asyncio
import sys
from dotenv import load_dotenv
from core.goals import get_goal_store
from core.model_check import run_preflight, print_report
from core.health import generate_health_report, print_health_report

load_dotenv()


def main():
    """
    Thin wrapper for goal injection and one-shot execution.
    For continuous autonomous operation, use council_daemon.py instead.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Autonomous Council - Goal Injection")
    parser.add_argument("--task", type=str, help="Task/goal description")
    parser.add_argument("--goal", type=str, help="Alias for --task")
    parser.add_argument("--health", action="store_true", help="Show health report")
    parser.add_argument("--preflight", action="store_true", help="Run preflight check")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip preflight check")
    
    args = parser.parse_args()
    
    if args.health:
        report = generate_health_report()
        print_health_report(report)
        return
    
    if args.preflight:
        report = run_preflight()
        print_report(report)
        sys.exit(0 if report["can_run"] else 1)
    
    task = args.task or args.goal
    if not task:
        task = input("Enter goal for the council: ").strip()
    
    if not task:
        print("No goal provided. Exiting.")
        return
    
    # Run preflight unless skipped
    if not args.skip_preflight:
        print("Running preflight check...")
        preflight = run_preflight()
        print_report(preflight)
        
        if not preflight["can_run"]:
            print("Preflight failed. Fix issues before running.")
            sys.exit(1)
    
    # Create goal
    goal_store = get_goal_store()
    goal_id = goal_store.create_goal(task, source="human", priority=10)
    
    print(f"\n✅ Goal created: {goal_id}")
    print(f"Description: {task}")
    print(f"\nTo run the autonomous council: python council_daemon.py --interval 60")
    print(f"Or check status: python council_daemon.py --health")


if __name__ == "__main__":
    main()
