from core.state_manager import load_checkpoint, list_checkpoints

def recover_latest():
    checkpoints = list_checkpoints()
    if not checkpoints:
        return None
    # Load most recent checkpoint
    latest = sorted(checkpoints)[-1]
    return load_checkpoint(latest)

def verify_state_integrity(state):
    # Placeholder for future integrity checks (e.g., schema validation)
    return state is not None
