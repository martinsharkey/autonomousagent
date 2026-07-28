"""Self-evolution feedback loop analyzer: extracts patterns from mutation outcomes."""
import json
import os
from typing import Dict, List, Optional

class EvolutionAnalyzer:
    """Analyzes mutation outcomes to extract learning patterns and recommendations."""

    def __init__(self, history_path: str = "mutation_history.json"):
        self.history_path = history_path
        self.history = self._load_history()

    def _load_history(self) -> List[Dict]:
        if os.path.exists(self.history_path):
            with open(self.history_path, "r") as f:
                return json.load(f)
        return []

    def record_outcome(self, mutation: Dict, success: bool, notes: str = ""):
        """Record the outcome of a mutation."""
        entry = {
            "mutation": mutation,
            "success": success,
            "notes": notes,
            "timestamp": __import__("time").time()
        }
        self.history.append(entry)
        self._save_history()

    def _save_history(self):
        with open(self.history_path, "w") as f:
            json.dump(self.history, f, indent=2)

    def get_patterns(self) -> Dict:
        """Extract patterns from mutation history."""
        if not self.history:
            return {"patterns": [], "recommendations": []}

        successes = [h for h in self.history if h["success"]]
        failures = [h for h in self.history if not h["success"]]

        patterns = []
        recommendations = []

        # Analyze success patterns
        if successes:
            success_types = {}
            for s in successes:
                mtype = s["mutation"].get("mutation_type", "unknown")
                success_types[mtype] = success_types.get(mtype, 0) + 1
            best_type = max(success_types, key=success_types.get)
            patterns.append(f"Most successful mutation type: {best_type} ({success_types[best_type]} successes)")
            recommendations.append(f"Prioritize {best_type} mutations in future proposals.")

        # Analyze failure patterns
        if failures:
            failure_notes = [f["notes"] for f in failures if f["notes"]]
            if failure_notes:
                common_notes = max(set(failure_notes), key=failure_notes.count)
                patterns.append(f"Common failure note: {common_notes}")
                recommendations.append(f"Avoid mutations that cause: {common_notes}")

        # Overall success rate
        total = len(self.history)
        success_rate = len(successes) / total if total > 0 else 0
        patterns.append(f"Overall success rate: {success_rate:.2f}")
        if success_rate < 0.5:
            recommendations.append("Consider smaller, lower-risk mutations to improve success rate.")

        return {
            "patterns": patterns,
            "recommendations": recommendations,
            "success_rate": success_rate,
            "total_mutations": total
        }

    def get_recent_failures(self, n: int = 5) -> List[Dict]:
        """Return the most recent n failures."""
        failures = [h for h in self.history if not h["success"]]
        return failures[-n:]
