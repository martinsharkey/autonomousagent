#!/usr/bin/env python3
"""Error pattern learning tool for recursive self-evolution.

Records failed tool invocations, clusters similar errors, and suggests
corrective actions to improve future performance.
"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Storage file for error logs
ERROR_LOG_PATH = Path(os.getenv('ERROR_LOG_PATH', 'data/error_log.jsonl'))

# Simple in-memory cache for recent errors
_recent_errors = []


def _ensure_storage():
    """Create storage directory if needed."""
    ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def record_error(tool_name: str, error_message: str, context: dict = None) -> dict:
    """Record a failed tool invocation with context.

    Args:
        tool_name: Name of the tool that failed.
        error_message: The error message or exception text.
        context: Optional dict with additional context (e.g., arguments, state).

    Returns:
        Dict with status and error_id.
    """
    _ensure_storage()
    error_id = f"err_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    entry = {
        'id': error_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'tool_name': tool_name,
        'error_message': error_message,
        'context': context or {},
    }
    with open(ERROR_LOG_PATH, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    _recent_errors.append(entry)
    # Keep only last 100 in memory
    if len(_recent_errors) > 100:
        _recent_errors.pop(0)
    return {'status': 'recorded', 'error_id': error_id}


def _normalize_error(message: str) -> str:
    """Normalize error message to extract pattern key."""
    # Remove variable parts like numbers, hashes, paths
    msg = re.sub(r'\b[0-9a-f]{8,}\b', 'HASH', message)
    msg = re.sub(r'\b\d+\b', 'NUM', msg)
    msg = re.sub(r'/[\w./-]+', 'PATH', msg)
    # Lowercase and strip whitespace
    return ' '.join(msg.lower().split())


def analyze_errors(limit: int = 50) -> dict:
    """Analyze recent errors and return pattern clusters with suggestions.

    Args:
        limit: Number of recent errors to analyze.

    Returns:
        Dict with clusters, suggestions, and stats.
    """
    _ensure_storage()
    errors = []
    if ERROR_LOG_PATH.exists():
        with open(ERROR_LOG_PATH, 'r') as f:
            for line in f:
                try:
                    errors.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    errors = errors[-limit:]

    # Cluster by normalized error message
    clusters = defaultdict(list)
    for err in errors:
        key = _normalize_error(err.get('error_message', ''))
        clusters[key].append(err)

    # Build suggestions based on common patterns
    suggestions = []
    for key, items in clusters.items():
        if len(items) < 2:
            continue
        tool_names = set(i['tool_name'] for i in items)
        suggestion = {
            'pattern': key,
            'occurrences': len(items),
            'tools': list(tool_names),
            'suggestion': _generate_suggestion(key, tool_names)
        }
        suggestions.append(suggestion)

    # Sort by occurrences descending
    suggestions.sort(key=lambda x: x['occurrences'], reverse=True)

    return {
        'total_errors_analyzed': len(errors),
        'unique_patterns': len(clusters),
        'suggestions': suggestions[:5],
        'recent_errors': errors[-5:]
    }


def _generate_suggestion(pattern: str, tools: set) -> str:
    """Generate a corrective action suggestion based on error pattern."""
    if 'timeout' in pattern or 'timed out' in pattern:
        return 'Consider adding retry logic with exponential backoff or increasing timeout.'
    if 'not found' in pattern or 'no such file' in pattern:
        return 'Verify file paths and ensure required resources exist before invocation.'
    if 'permission' in pattern or 'denied' in pattern:
        return 'Check permissions and ensure the agent has necessary access rights.'
    if 'invalid' in pattern or 'bad request' in pattern:
        return 'Validate inputs and parameters before calling the tool.'
    if 'connection' in pattern or 'network' in pattern:
        return 'Implement network resilience: retry, fallback, or circuit breaker.'
    return 'Review the tool usage pattern and consider adding pre-checks or fallbacks.'


def clear_errors() -> dict:
    """Clear the error log (for testing or reset)."""
    if ERROR_LOG_PATH.exists():
        ERROR_LOG_PATH.unlink()
    _recent_errors.clear()
    return {'status': 'cleared'}


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'analyze':
        print(json.dumps(analyze_errors(), indent=2))
    else:
        print('Usage: python tools/error_learning.py analyze')
