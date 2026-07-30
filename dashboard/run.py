import uvicorn


def run_dashboard(host: str = "0.0.0.0", port: int = 8000):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    uvicorn.run("core.dashboard:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run_dashboard()
