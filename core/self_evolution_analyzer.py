import json
from pathlib import Path
from typing import Dict, List, Tuple
from governance.audit_log import AuditLog
from governance.consensus import CouncilVote

class SelfEvolutionAnalyzer:
    def __init__(self, audit_log_path: str = "governance/audit_log.json", council_votes_path: str = "governance/council_votes.json"):
        self.audit_log_path = Path(audit_log_path)
        self.council_votes_path = Path(council_votes_path)
        self.learning_patterns = []

    def load_audit_logs(self) -> List[Dict]:
        if not self.audit_log_path.exists():
            return []
        with open(self.audit_log_path, 'r') as f:
            return json.load(f)

    def load_council_votes(self) -> List[Dict]:
        if not self.council_votes_path.exists():
            return []
        with open(self.council_votes_path, 'r') as f:
            return json.load(f)

    def extract_mutation_outcomes(self) -> Dict[str, Dict]:
        """Extract mutation outcomes from audit logs and council votes."""
        audit_logs = self.load_audit_logs()
        council_votes = self.load_council_votes()
        outcomes = {}

        for log in audit_logs:
            if log.get('event_type') == 'mutation_evaluation':
                mutation_id = log.get('mutation_id')
                if mutation_id:
                    outcomes[mutation_id] = {
                        'status': log.get('status'),
                        'risk_level': log.get('risk_level'),
                        'test_results': log.get('test_results', []),
                        'timestamp': log.get('timestamp')
                    }

        for vote in council_votes:
            mutation_id = vote.get('mutation_id')
            if mutation_id and mutation_id in outcomes:
                outcomes[mutation_id]['council_vote'] = vote.get('vote_result')

        return outcomes

    def identify_learning_patterns(self) -> List[Dict]:
        """Identify patterns in mutation outcomes to guide future self-evolution."""
        outcomes = self.extract_mutation_outcomes()
        patterns = []

        # Group outcomes by mutation type
        mutation_types = {}
        for mutation_id, data in outcomes.items():
            mutation_type = data.get('mutation_type', 'unknown')
            if mutation_type not in mutation_types:
                mutation_types[mutation_type] = []
            mutation_types[mutation_type].append(data)

        # Analyze patterns per mutation type
        for mutation_type, type_outcomes in mutation_types.items():
            successful = [o for o in type_outcomes if o.get('status') == 'promoted']
            failed = [o for o in type_outcomes if o.get('status') in ['rolled_back', 'failed']]

            if successful and failed:
                patterns.append({
                    'mutation_type': mutation_type,
                    'success_rate': len(successful) / len(type_outcomes),
                    'common_risk_factors': self._extract_common_risk_factors(type_outcomes),
                    'test_coverage_issues': self._identify_test_coverage_gaps(type_outcomes),
                    'recommendations': self._generate_recommendations(mutation_type, successful, failed)
                })

        self.learning_patterns = patterns
        return patterns

    def _extract_common_risk_factors(self, outcomes: List[Dict]) -> List[str]:
        """Extract common risk factors from failed mutations."""
        risk_factors = []
        for outcome in outcomes:
            if outcome.get('status') in ['rolled_back', 'failed']:
                risk_factors.extend(outcome.get('risk_factors', []))
        return list(set(risk_factors))

    def _identify_test_coverage_gaps(self, outcomes: List[Dict]) -> List[str]:
        """Identify gaps in test coverage for mutation types."""
        gaps = []
        for outcome in outcomes:
            if outcome.get('status') in ['rolled_back', 'failed']:
                test_results = outcome.get('test_results', [])
                if not test_results or all(tr.get('status') == 'failed' for tr in test_results):
                    gaps.append(f"Insufficient test coverage for {outcome.get('mutation_type')}")
        return list(set(gaps))

    def _generate_recommendations(self, mutation_type: str, successful: List[Dict], failed: List[Dict]) -> List[str]:
        """Generate recommendations for improving mutation success rate."""
        recommendations = []

        if mutation_type == 'parameter_adjustment':
            recommendations.append("Prioritize parameter adjustments with council-approved risk thresholds")
            recommendations.append("Implement canary testing for parameter changes before fleet rollout")

        elif mutation_type == 'tool_addition':
            recommendations.append("Require static analysis validation for new tools")
            recommendations.append("Implement sandbox execution for high-risk tool additions")

        elif mutation_type == 'strategy_evolution':
            recommendations.append("Use council votes to validate strategic shifts before implementation")
            recommendations.append("Monitor alignment scores post-strategy change")

        # Add type-specific recommendations based on success/failure patterns
        if successful and not failed:
            recommendations.append("This mutation type shows high success rate; consider expanding scope")
        elif failed and not successful:
            recommendations.append("This mutation type consistently fails; review approach or halt further mutations")

        return recommendations

    def log_learning_patterns(self, patterns: List[Dict]):
        """Log identified learning patterns for future reference."""
        with open("core/learning_patterns.json", 'w') as f:
            json.dump(patterns, f, indent=2)

    def run_analysis(self):
        """Run full analysis and log results."""
        patterns = self.identify_learning_patterns()
        self.log_learning_patterns(patterns)
        return patterns