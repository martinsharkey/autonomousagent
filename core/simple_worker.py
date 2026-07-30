import asyncio
from typing import Dict, Any


async def process_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Simple worker that processes a task and returns a result."""
    task_text = task.get("task", "")
    return {
        "status": "completed",
        "task": task_text,
        "result": f"Processed task: {task_text[:100]}",
    }
