import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict
import sqlite3
from core.goals import GoalStore

@dataclass
class FailurePattern:
    pattern_id: str
    description: str
    frequency: int
    affected_goals: List[str]
    suggested_improvements: List[str]
    severity: float  # 0.0 to 1.0

class FailureAnalyzer:
    def __init__(self, db_path: str = "core/agent_state.db"):
        self.db_path = db_path
        self.goal_store = GoalStore(db_path)

    def analyze_trajectories(self, limit: int = 100) -> List[FailurePattern]:
        """Analyze recent trajectories to identify failure patterns."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Fetch recent trajectories
        cursor.execute(
            """
            SELECT trajectory_id, goal_id, outcome, timestamp, metadata
            FROM trajectories
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,)
        )
        trajectories = cursor.fetchall()

        # Group by goal and outcome
        goal_outcomes = defaultdict(list)
        for traj in trajectories:
            goal_id = traj[1]
            outcome = traj[2]
            goal_outcomes[goal_id].append(outcome)

        # Identify patterns
        patterns = []
        for goal_id, outcomes in goal_outcomes.items():
            goal = self.goal_store.get_goal(goal_id)
            if not goal:
                continue

            # Simple pattern detection: count failures per goal
            failure_count = sum(1 for o in outcomes if o == "failure")
            total_count = len(outcomes)
            failure_rate = failure_count / total_count if total_count > 0 else 0.0

            if failure_rate > 0.3:  # Threshold for significant failure rate
                pattern = FailurePattern(
                    pattern_id=f"goal_{goal_id}_failure_pattern",
                    description=f"Goal '{goal.name}' fails {failure_rate*100:.1f}% of the time",
                    frequency=failure_count,
                    affected_goals=[goal_id],
                    suggested_improvements=[
                        "Review goal criteria and evaluation metrics",
                        "Adjust strategy parameters for this goal",
                        "Check tool availability and reliability for this goal",
                        "Consider splitting this goal into sub-goals"
                    ],
                    severity=min(failure_rate, 0.9)  # Cap severity at 0.9
                )
                patterns.append(pattern)

        # Additional pattern: recurring tool failures
        cursor.execute(
            """
            SELECT tool_name, COUNT(*) as failure_count
            FROM tool_invocations
            WHERE outcome = 'failure'
            GROUP BY tool_name
            ORDER BY failure_count DESC
            LIMIT 10
            """
        )
        tool_failures = cursor.fetchall()
        for tool_name, count in tool_failures:
            if count > 3:  # Threshold for significant tool failures
                pattern = FailurePattern(
                    pattern_id=f"tool_{tool_name}_failure_pattern",
                    description=f"Tool '{tool_name}' fails {count} times",
                    frequency=count,
                    affected_goals=[],  # Could be associated with goals later
                    suggested_improvements=[
                        f"Review tool implementation for {tool_name}",
                        "Check tool dependencies and environment",
                        "Consider alternative tools or implementations",
                        "Add more robust error handling in the tool"
                    ],
                    severity=min(count / 20.0, 0.8)  # Normalize and cap
                )
                patterns.append(pattern)

        conn.close()
        return patterns

    def generate_recommendations(self, patterns: List[FailurePattern]) -> Dict:
        """Generate actionable recommendations based on identified patterns."""
        recommendations = {
            "patterns": [p.__dict__ for p in patterns],
            "actions": [],
            "priorities": []
        }

        # Generate recommendations based on patterns
        for pattern in patterns:
            if pattern.severity > 0.5:
                recommendations["priorities"].append({
                    "pattern_id": pattern.pattern_id,
                    "severity": pattern.severity,
                    "action": f"Address high-severity failure pattern: {pattern.description}"
                })

            # Add specific actions for each pattern type
            if "goal" in pattern.pattern_id:
                recommendations["actions"].append({
                    "type": "goal_review",
                    "target": pattern.affected_goals[0],
                    "details": pattern.suggested_improvements
                })
            elif "tool" in pattern.pattern_id:
                recommendations["actions"].append({
                    "type": "tool_review",
                    "target": pattern.pattern_id.split("_")[1],
                    "details": pattern.suggested_improvements
                })

        return recommendations

    def get_failure_report(self) -> Dict:
        """Generate a comprehensive failure report with patterns and recommendations."""
        patterns = self.analyze_trajectories()
        return self.generate_recommendations(patterns)