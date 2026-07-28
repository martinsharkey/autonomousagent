import json
from pathlib import Path
from typing import Dict, List
from core.self_evolution_analyzer import SelfEvolutionAnalyzer

# Add to EvolutionEngine class
class EvolutionEngine:
    def __init__(self):
        self.analyzer = SelfEvolutionAnalyzer()

    def evaluate_mutation(self, mutation: Dict) -> Dict:
        """Enhanced mutation evaluation with learning pattern integration."""
        # Existing evaluation logic...
        result = self._base_evaluate_mutation(mutation)

        # Integrate learning patterns into evaluation
        patterns = self.analyzer.identify_learning_patterns()
        mutation_type = mutation.get('mutation_type', 'unknown')

        for pattern in patterns:
            if pattern['mutation_type'] == mutation_type:
                # Adjust risk assessment based on historical patterns
                if pattern['success_rate'] < 0.3:
                    result['risk_level'] = 'high'  # Override if historically low success
                elif pattern['success_rate'] > 0.8:
                    result['risk_level'] = 'low'  # Override if historically high success

                # Add pattern-based recommendations
                result['learning_recommendations'] = pattern.get('recommendations', [])

        return result

    def _base_evaluate_mutation(self, mutation: Dict) -> Dict:
        """Original mutation evaluation logic (preserved)."""
        # ... existing implementation ...