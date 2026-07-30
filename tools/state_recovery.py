import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path("checkpoints")
CHECKPOINT_DIR.mkdir(exist_ok=True)

def _load_checkpoint(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r") as f:
            data = json.load(f)
        # Basic integrity check: must have 'state' and 'version' keys
        if "state" not in data or "version" not in data:
            logger.warning(f"Checkpoint {path} missing required keys")
            return None
        return data
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load checkpoint {path}: {e}")
        return None

def recover_state() -> Optional[Dict[str, Any]]:
    """Recover the most recent valid checkpoint."""
    checkpoints = sorted(CHECKPOINT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for cp in checkpoints:
        data = _load_checkpoint(cp)
        if data is not None:
            logger.info(f"Recovered state from {cp}")
            return data["state"]
    logger.error("No valid checkpoint found for recovery")
    return None

def validate_checkpoint(path: str) -> bool:
    """Validate a specific checkpoint file."""
    p = Path(path)
    if not p.exists():
        logger.error(f"Checkpoint {path} does not exist")
        return False
    return _load_checkpoint(p) is not None
