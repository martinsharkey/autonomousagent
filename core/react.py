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
    import traceback
    tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    return {
        "node": node,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": tb_str,
        "context": context or {},
    }


def build_self_correction_prompt(role_name: str, last_error: Dict[str, Any], reasoning_traces: List[str]) -> str:
    """Build a self-correction prompt from the latest error feedback."""
    error_type = last_error.get("error_type", "Unknown")
    error_message = last_error.get("error_message", "Unknown error")
    context = last_error.get("context", {})
    trace_history = "\n".join(reasoning_traces[-5:]) if reasoning_traces else "- no prior reasoning traces"
    
    return f"""Council member: {role_name}

PREVIOUS ATTEMPT FAILED
Error Type: {error_type}
Error Message: {error_message}
Context: {json.dumps(context, default=str)}

Recent Reasoning Traces:
{trace_history}

Your last attempt caused a crash. You must diagnose why and propose a corrected action.

Requirements:
1. In <think>: analyze the stack trace and identify the root cause
2. In <action>: output a JSON object with:
   - diagnosis: brief root cause
   - correction: specific fix or alternative approach
   - confidence: 0.0-1.0
"""
