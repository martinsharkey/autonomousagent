import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Council Dashboard")

templates = Jinja2Templates(directory="dashboard/templates")
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")


def _safe_get_status() -> Dict[str, Any]:
    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "goals": [],
        "mutations": [],
        "agents": ["autobot", "alpha_evaluator", "beta_worker"],
    }
    try:
        from core.goals import get_goal_store
        goal_store = get_goal_store()
        status["goals"] = goal_store.get_recent_goals(limit=20)
    except Exception:
        pass
    return status


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    status = _safe_get_status()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "status": status,
    })


@app.get("/api/status")
async def api_status():
    return JSONResponse(_safe_get_status())


@app.post("/api/goal")
async def api_create_goal(payload: Dict[str, Any]):
    description = payload.get("description", "")
    if not description:
        return JSONResponse({"error": "description required"}, status_code=400)
    try:
        from core.goals import get_goal_store
        goal_id = get_goal_store().create_goal(description, source="web")
        return JSONResponse({"goal_id": goal_id, "description": description})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/api/goals")
async def api_goals(limit: int = 20):
    try:
        from core.goals import get_goal_store
        goals = get_goal_store().get_recent_goals(limit=limit)
        return JSONResponse(goals)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
