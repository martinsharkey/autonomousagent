import json
import logging
from typing import Dict, List, Optional
from core.learning import LearningModule

logger = logging.getLogger(__name__)

class SelfReflectionTool:
    """Analyzes recent trajectories and generates improvement suggestions."""

    def __init__(self, learning_module: Optional[LearningModule] = None):
        self.learning = learning_module or LearningModule()

    def analyze(self, trajectories: List[Dict], success_rate: float) -> Dict:
        """
        Analyze recent trajectories and success rate to produce suggestions.
        
        Args:
            trajectories: List of recent tool invocation records.
            success_rate: Float between 0.0 and 1.0.
        
        Returns:
            Dict with 'suggestions' (list of strings) and 'patterns' (list of dicts).
        """
        suggestions = []
        patterns = []

        if not trajectories:
            suggestions.append("No trajectory data available; consider enabling detailed logging.")
            return {"suggestions": suggestions, "patterns": patterns}

        # Identify common failure patterns
        failures = [t for t in trajectories if t.get('status') == 'failure']
        if failures:
            error_types = {}
            for f in failures:
                err = f.get('error', 'unknown')
                error_types[err] = error_types.get(err, 0) + 1
            for err, count in sorted(error_types.items(), key=lambda x: -x[1]):
                patterns.append({"type": "failure", "error": err, "count": count})
                if count > len(failures) * 0.3:
                    suggestions.append(f"Frequent error '{err}' ({count} times); consider adding retry logic or pre-validation.")

        # Identify successful patterns
        successes = [t for t in trajectories if t.get('status') == 'success']
        if successes:
            tool_counts = {}
            for s in successes:
                tool = s.get('tool', 'unknown')
                tool_counts[tool] = tool_counts.get(tool, 0) + 1
            for tool, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
                if count > len(successes) * 0.5:
                    suggestions.append(f"Tool '{tool}' is highly successful ({count} times); consider prioritizing it.")

        # General suggestions based on success rate
        if success_rate < 0.3:
            suggestions.append("Low success rate; consider reducing task complexity or increasing validation.")
        elif success_rate > 0.8:
            suggestions.append("High success rate; consider tackling more ambitious tasks.")

        # Store patterns in learning module for future reference
        try:
            self.learning.store_patterns(patterns)
        except Exception as e:
            logger.warning(f"Failed to store patterns: {e}")

        return {"suggestions": suggestions, "patterns": patterns}
