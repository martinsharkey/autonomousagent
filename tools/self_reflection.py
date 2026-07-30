"""Tool for self-reflection and error analysis to drive recursive self-evolution."""
import json
import traceback
from typing import Dict, Any, Optional
from datetime import datetime

class SelfReflectionTool:
    """Analyzes recent failures, extracts patterns, and proposes corrective actions."""

    def __init__(self, log_path: str = "session_log.md"):
        self.log_path = log_path

    def analyze_failure(self, error_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a failure context and return structured reflection.
        
        Args:
            error_context: Dict with keys 'error_type', 'error_message', 'traceback', 'tool_used', 'input_data'
        
        Returns:
            Dict with 'root_cause', 'suggested_fix', 'preventive_measure', 'confidence'
        """
        error_type = error_context.get('error_type', 'Unknown')
        error_msg = error_context.get('error_message', '')
        tb = error_context.get('traceback', '')
        tool_used = error_context.get('tool_used', 'unknown')
        
        # Pattern matching for common errors
        root_cause = "Unknown"
        suggested_fix = "Review logs and retry"
        preventive_measure = "Add more robust error handling"
        confidence = 0.3
        
        if 'ConnectionError' in error_type or 'Timeout' in error_type:
            root_cause = "Network or API unavailability"
            suggested_fix = "Implement retry with exponential backoff"
            preventive_measure = "Add health checks before API calls"
            confidence = 0.7
        elif 'KeyError' in error_type or 'AttributeError' in error_type:
            root_cause = "Missing expected data field"
            suggested_fix = "Add defensive checks for missing keys"
            preventive_measure = "Validate input schema before processing"
            confidence = 0.8
        elif 'PermissionError' in error_type:
            root_cause = "Insufficient permissions"
            suggested_fix = "Check file/API permissions"
            preventive_measure = "Preflight permission checks"
            confidence = 0.9
        elif 'ValueError' in error_type:
            root_cause = "Invalid input value"
            suggested_fix = "Add input validation and sanitization"
            preventive_measure = "Type checking and range validation"
            confidence = 0.6
        
        # Log the reflection
        self._log_reflection(error_context, root_cause, suggested_fix, preventive_measure, confidence)
        
        return {
            "root_cause": root_cause,
            "suggested_fix": suggested_fix,
            "preventive_measure": preventive_measure,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _log_reflection(self, context: Dict[str, Any], root_cause: str, fix: str, prevention: str, confidence: float):
        """Append reflection to session log for audit trail."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "context": context,
            "analysis": {
                "root_cause": root_cause,
                "suggested_fix": fix,
                "preventive_measure": prevention,
                "confidence": confidence
            }
        }
        try:
            with open(self.log_path, 'a') as f:
                f.write(f"\n## Self-Reflection Entry\n```json\n{json.dumps(entry, indent=2)}\n```\n")
        except Exception:
            pass  # Fail silently if log write fails

    def get_recent_reflections(self, n: int = 5) -> list:
        """Retrieve last n reflections from log."""
        reflections = []
        try:
            with open(self.log_path, 'r') as f:
                content = f.read()
            # Simple extraction of JSON blocks after 'Self-Reflection Entry'
            import re
            blocks = re.findall(r'```json\n(.*?)\n```', content, re.DOTALL)
            for block in blocks[-n:]:
                try:
                    reflections.append(json.loads(block))
                except json.JSONDecodeError:
                    continue
        except FileNotFoundError:
            pass
        return reflections

    def generate_improvement_proposal(self) -> Optional[Dict[str, Any]]:
        """Aggregate recent reflections to propose a mutation."""
        reflections = self.get_recent_reflections(10)
        if not reflections:
            return None
        
        # Count root causes
        cause_counts = {}
        for ref in reflections:
            cause = ref.get('analysis', {}).get('root_cause', 'Unknown')
            cause_counts[cause] = cause_counts.get(cause, 0) + 1
        
        if not cause_counts:
            return None
        
        most_common = max(cause_counts, key=cause_counts.get)
        count = cause_counts[most_common]
        
        if count >= 3:
            return {
                "mutation_type": "strategy_evolution",
                "description": f"Auto-proposed mutation to address recurring failure: {most_common}",
                "rationale": f"Detected {count} occurrences of '{most_common}' in recent failures. Proposing targeted fix.",
                "risk_level": "medium",
                "expected_improvement": 0.3
            }
        return None
