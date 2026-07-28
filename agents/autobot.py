from tools.state_checkpoint_tool import StateCheckpointTool

class Autobot:
    def __init__(self):
        self.state_checkpoint_tool = StateCheckpointTool()
        self.local_state = {}
        # ... existing init code ...

    def initialize(self):
        """Initialize autobot with recovery from last valid checkpoint."""
        # Attempt to recover state from last valid checkpoint
        recovered_state = self.state_checkpoint_tool.recover_last_valid_state()
        if recovered_state:
            self.local_state = recovered_state
            print("[Autobot] Recovered state from checkpoint.")
        else:
            print("[Autobot] No valid state recovered; starting fresh.")
        # ... rest of initialization ...

    def update_state(self, new_state: Dict[str, Any]):
        """Update local state and create a checkpoint."""
        self.local_state.update(new_state)
        checkpoint_id = self.state_checkpoint_tool.create_checkpoint(self.local_state)
        if checkpoint_id:
            print(f"[Autobot] Created checkpoint {checkpoint_id}")
        # ... rest of state update logic ...

    def cleanup_checkpoints(self):
        """Clean up old checkpoints to optimize disk usage."""
        self.state_checkpoint_tool.cleanup_old_checkpoints()
