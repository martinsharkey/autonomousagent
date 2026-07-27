"""ReAct reasoning utilities for council agents."""
from __future__ import annotations

import re
from typing import Dict, Any, Optional, Tuple


REACT_THINK_PATTERN = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)
REACT_ACTION_PATTERN = re.compile(r"<action>(.*?)</action>", re.DOTALL | re.IGNORECASE)


def extract_react_parts(text: str) -> Tuple[str, str]:
    """Extract reasoning and action from ReAct formatted response."""
    think_match = REACT_THINK_PATTERN.search(text)
    action_match = REACT_ACTION_PATTERN.search(text)

    reasoning = think_match.group(1).strip() if think_match else ""
    action_text = action_match.group(1).strip() if action_match else text.strip()

    return reasoning, action_text


def build_react_system_prompt(base_prompt: str, role: str) -> str:
    """Wrap a base system prompt with universal ReAct instructions."""
    return f"""{base_prompt}

## ReAct Reasoning Protocol
You must always format your response as:

<think>
[Analyze the goal, review previous reasoning traces, audit assumptions, plan next steps or tool calls]
</think>
<action>
[Your structured output: JSON vote, tool call, or decision payload]
</action>

Rules:
- Always include both </think> and <action> blocks.
- Keep reasoning concise but explicit.
- In <action>, return only valid JSON or a clear command string.
- Do not include markdown fences in <action>.
- If no meaningful action is possible, return an empty JSON object {{}}.
"""


def build_react_voter_prompt(role_name: str, proposal_text: str, mission_rationale: str) -> str:
    """Build a ReAct-style mutation evaluation prompt."""
    return f"""
Council member: {role_name}

MISSION RATIONALE:
{mission_rationale}

PROPOSED MUTATION:
{proposal_text}

Evaluate this mutation. Then format your response:

<think>
[Assess risks, alignment, feasibility, and rationale quality. Reference prior reasoning traces if available.]
</think>
<action>
{{
  "vote": "APPROVE" or "REJECT",
  "confidence": 0.0-1.0,
  "reasoning": "brief reason"
}}
</action>
"""


def build_error_feedback(node: str, error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a structured error_feedback entry for AgentState."""
    return {
        "node": node,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {},
    }
