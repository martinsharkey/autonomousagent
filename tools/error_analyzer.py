import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

class ErrorAnalyzer:
    def __init__(self, db_path: str = "core/agent_state.db"):
        self.db_path = db_path
        self.error_categories = {
            "tool_failure": ["ToolInvocationError", "ToolNotFoundError", "ToolTimeoutError"],
            "llm_failure": ["LLMRequestError", "LLMResponseError", "LLMValidationError"],
            "resource_failure": ["ResourceExhaustionError", "RateLimitError", "MemoryError"],
            "system_failure": ["SystemError", "CheckpointError", "HealthCheckFailure"]
        }

    def analyze_recent_errors(self, time_window_hours: int = 24) -> Dict:
        """Analyze errors from the last N hours and categorize them"""
        cutoff = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all error logs
            cursor.execute("""
                SELECT error_type, error_message, timestamp, tool_name, context
                FROM error_logs
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (cutoff.isoformat(),))
            
            raw_errors = cursor.fetchall()
            
            # Categorize errors
            categorized = self._categorize_errors(raw_errors)
            
            # Generate improvement suggestions
            suggestions = self._generate_suggestions(categorized)
            
            return {
                "time_window_hours": time_window_hours,
                "total_errors": len(raw_errors),
                "error_categories": categorized,
                "improvement_suggestions": suggestions,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }

    def _categorize_errors(self, errors: List[Tuple]) -> Dict:
        """Categorize errors by type and frequency"""
        category_counts = {cat: 0 for cat in self.error_categories}
        category_details = {cat: [] for cat in self.error_categories}
        
        for error_type, error_msg, timestamp, tool_name, context in errors:
            for category, error_types in self.error_categories.items():
                if error_type in error_types:
                    category_counts[category] += 1
                    category_details[category].append({
                        "error_type": error_type,
                        "error_message": error_msg,
                        "timestamp": timestamp,
                        "tool_name": tool_name,
                        "context": context
                    })
                    break
        
        return {
            "counts": category_counts,
            "details": category_details
        }

    def _generate_suggestions(self, categorized: Dict) -> List[Dict]:
        """Generate specific improvement suggestions based on error patterns"""
        suggestions = []
        
        # Tool failure suggestions
        if categorized["counts"]["tool_failure"] > 0:
            suggestions.append({
                "category": "tool_failure",
                "priority": "high",
                "actions": [
                    "Review tool implementations for error handling",
                    "Add retry logic with exponential backoff for transient failures",
                    "Implement circuit breakers for frequently failing tools"
                ],
                "rationale": f"{categorized['counts']['tool_failure']} tool failures detected in the last window"
            })
        
        # LLM failure suggestions
        if categorized["counts"]["llm_failure"] > 0:
            suggestions.append({
                "category": "llm_failure",
                "priority": "high",
                "actions": [
                    "Implement provider fallback logic in core/api_router.py",
                    "Add input validation for LLM prompts",
                    "Implement response caching for repeated queries",
                    "Review model selection strategy"
                ],
                "rationale": f"{categorized['counts']['llm_failure']} LLM failures detected in the last window"
            })
        
        # Resource exhaustion suggestions
        if categorized["counts"]["resource_failure"] > 0:
            suggestions.append({
                "category": "resource_failure",
                "priority": "critical",
                "actions": [
                    "Implement dynamic resource throttling",
                    "Add memory monitoring and cleanup routines",
                    "Review free tier usage patterns",
                    "Implement cost-aware tool selection"
                ],
                "rationale": f"{categorized['counts']['resource_failure']} resource exhaustion events detected"
            })
        
        # System failure suggestions
        if categorized["counts"]["system_failure"] > 0:
            suggestions.append({
                "category": "system_failure",
                "priority": "critical",
                "actions": [
                    "Review checkpointing strategy",
                    "Implement health check improvements",
                    "Add system recovery procedures",
                    "Review state management"
                ],
                "rationale": f"{categorized['counts']['system_failure']} system failures detected"
            })
        
        # General improvement suggestions
        if not any(categorized["counts"].values()):
            suggestions.append({
                "category": "general",
                "priority": "low",
                "actions": [
                    "Review recent successful operations for patterns",
                    "Analyze performance metrics for optimization opportunities",
                    "Consider adding more diverse tooling"
                ],
                "rationale": "No errors detected in the analysis window - focusing on proactive improvements"
            })
        
        return suggestions

def main():
    analyzer = ErrorAnalyzer()
    results = analyzer.analyze_recent_errors()
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()