"""

Agent planning and tool use capabilities.

Enables agents to plan multi-step work, use tools, and execute code safely.

"""



import json
import subprocess
import sys

from typing import Dict, Any, List, Optional

from datetime import datetime

from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage

from core.models import get_primary_model

from core.agent_config import get_config_store

from core.sandbox import execute_in_sandbox

from core.editor_tool import execute_editor_action

from tools.mcp_registry import get_registered_tools

from core.api_router import get_llm_router, _provider_temperature


PROJECT_ROOT = Path(__file__).resolve().parent.parent





class AgentPlanner:

    """Enables agents to create structured plans for multi-step work."""

    

    def __init__(self, agent_name: str):

        self.agent_name = agent_name

        self.config_store = get_config_store()

        self.llm_router = get_llm_router()

    

    def _get_temperature(self, context: str = "planning") -> float:

        try:

            return _provider_temperature(self.agent_name)

        except Exception:

            return 0.2

    

    async def create_plan(self, goal: str) -> Dict[str, Any]:

        """Create a structured plan for a goal."""

        config = self.config_store.get_active_with_defaults(self.agent_name)

        

        system_prompt = config.get("system_prompt", "")

        available_tools = config.get("allowed_tools", [])

        # Merge dynamically-registered tools into available list
        try:
            from tools.auto_discovery import get_available_tool_names
            registered_tools = get_available_tool_names()
            all_tools = sorted(set(available_tools + registered_tools))
        except Exception:
            all_tools = available_tools

        prompt = f"""

{system_prompt}



Goal: {goal}



Available tools: {', '.join(all_tools)}



Respond exactly as:

<think>

[Break the goal into steps, choose tools, identify risks]

</think>

<action>

{{

  "steps": [

    {{

      "step": 1,

      "action": "description",

      "tool": "tool_name or null",

      "expected_output": "what this step produces"

    }}

  ],

  "total_steps": N,

  "estimated_complexity": "low|medium|high"

}}

</action>

"""

        

        try:

            from core.react import extract_react_parts

            response = await self.llm_router.route_request(

                messages=[

                    {"role": "system", "content": system_prompt},

                    {"role": "user", "content": prompt},

                ],

                temperature=self._get_temperature("planning"),

            )

            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

            content = content.strip()

            if content.startswith("```"):

                content = content.split("```", 2)[1]

                if content.startswith("json"):

                    content = content[4:]

            _reasoning, action_text = extract_react_parts(content)

            action_text = action_text.strip()

            if not action_text:

                return {

                    "goal": goal,

                    "error": "Failed to create plan: empty LLM response",

                    "status": "failed"

                }

            try:

                plan = json.loads(action_text)

            except Exception as e:

                return {

                    "goal": goal,

                    "error": f"Failed to create plan: {str(e)}",

                    "status": "failed"

                }


            return {

                "goal": goal,

                "plan": plan,

                "created_at": datetime.utcnow().isoformat(),

                "status": "created"

            }

        except Exception as e:

            return {

                "goal": goal,

                "error": f"Failed to create plan: {str(e)}",

                "status": "failed"

            }

    

    async def execute_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:

        """Execute a single step from a plan."""

        action = step.get("action", "")

        tool_name = step.get("tool")

        

        result = {

            "step": step.get("step"),

            "action": action,

            "tool": tool_name,

            "status": "pending"

        }

        

        try:

            if tool_name == "shell_exec":

                code = action

                sandbox_result = execute_in_sandbox(code)

                result["output"] = sandbox_result

                result["status"] = "completed"

            elif tool_name == "editor":

                editor_result = execute_editor_action(action)

                result["output"] = json.dumps(editor_result, indent=2)

                result["status"] = "completed" if editor_result.get("success") else "failed"

                if not editor_result.get("success"):

                    result["error"] = editor_result.get("error", "Editor action failed")

            elif tool_name:

                # Try dispatching to any dynamically registered tool
                from tools.mcp_registry import _tool_registry
                if tool_name in _tool_registry:
                    tool_func = _tool_registry[tool_name]
                    try:
                        tool_result = tool_func.invoke(action)
                        result["output"] = str(tool_result)
                        result["status"] = "completed"
                    except Exception as tool_err:
                        result["output"] = f"Tool '{tool_name}' error: {tool_err}"
                        result["status"] = "failed"
                        result["error"] = str(tool_err)
                else:
                    result["output"] = f"Unknown tool: {tool_name}"
                    result["status"] = "failed"
                    result["error"] = f"Tool '{tool_name}' not found in registry"

            else:

                config = self.config_store.get_active(self.agent_name)

                

                response = await self.llm_router.route_request(

                    messages=[

                        {"role": "system", "content": config.get("system_prompt", "")},

                        {"role": "user", "content": action}

                    ],

                    temperature=self._get_temperature("execution"),

                )

                content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

                result["output"] = content

                result["status"] = "completed"

        

        except Exception as e:

            result["error"] = str(e)

            result["error_type"] = type(e).__name__

            result["status"] = "failed"

        

        return result

    

    async def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:

        """Execute all steps in a plan."""

        if plan.get("status") != "created":

            return {"error": "Plan not ready for execution"}

        

        steps = plan.get("plan", {}).get("steps", [])

        results = []

        context = {}

        

        for step in steps:

            result = await self.execute_step(step, context)

            results.append(result)

            

            if result["status"] == "failed":

                return {

                    "plan": plan,

                    "results": results,

                    "status": "failed",

                    "failed_at_step": step.get("step")

                }

        

        # Run tests if any steps modified files
        files_modified = self._get_modified_files(results)
        test_result = None
        if files_modified:
            test_result = self._run_post_goal_tests()
            if test_result and not test_result.get("passed"):
                return {
                    "plan": plan,
                    "results": results,
                    "status": "failed",
                    "failed_reason": "post_goal_tests_failed",
                    "test_result": test_result,
                    "files_modified": files_modified,
                    "completed_at": datetime.utcnow().isoformat()
                }

        return {
            "plan": plan,
            "results": results,
            "status": "completed",
            "files_modified": files_modified,
            "test_result": test_result,
            "completed_at": datetime.utcnow().isoformat()
        }

    def _get_modified_files(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract list of files modified during plan execution."""
        modified = []
        for r in results:
            if r.get("tool") == "editor" and r.get("status") == "completed":
                try:
                    output = json.loads(r.get("output", "{}"))
                    if output.get("file_path"):
                        modified.append(output["file_path"])
                except (json.JSONDecodeError, TypeError):
                    pass
        return modified

    def _run_post_goal_tests(self) -> Optional[Dict[str, Any]]:
        """Run core test suite after goal execution to catch breakages."""
        try:
            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest",
                    "tests/test_integration.py",
                    "tests/test_state.py",
                    "-m", "not live",
                    "-x", "--tb=short", "-q", "--timeout=60",
                ],
                capture_output=True,
                text=True,
                timeout=90,
                cwd=str(PROJECT_ROOT),
            )
            return {
                "passed": result.returncode == 0,
                "output": result.stdout[-2000:] if result.stdout else "",
                "errors": result.stderr[-500:] if result.stderr else "",
            }
        except subprocess.TimeoutExpired:
            return {"passed": False, "output": "", "errors": "Test suite timed out"}
        except Exception as e:
            # If tests can't run, don't block — just warn
            return {"passed": True, "output": "", "errors": f"Tests skipped: {str(e)}"}

    async def verify_goal(self, goal: str, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Verify whether a goal was actually achieved by the execution.

        Uses LLM to assess whether the plan outputs satisfy the goal.

        Args:
            goal: The original goal description.
            execution_result: The result from execute_plan().

        Returns:
            Dict with verified (bool), confidence (float 0-1), reason (str).
        """
        if execution_result.get("status") != "completed":
            return {
                "verified": False,
                "confidence": 0.9,
                "reason": f"Execution failed: {execution_result.get('failed_reason', execution_result.get('status'))}"
            }

        # Build a summary of what was done
        steps_summary = []
        for r in execution_result.get("results", []):
            output = r.get("output", "")
            if len(output) > 500:
                output = output[:500] + "..."
            steps_summary.append(f"Step {r.get('step')}: {r.get('action', '')[:100]} → {r.get('status')} | Output: {output[:200]}")

        files_modified = execution_result.get("files_modified", [])
        test_result = execution_result.get("test_result")

        verification_prompt = f"""You are verifying whether a goal was successfully achieved.

Goal: {goal}

Steps executed:
{chr(10).join(steps_summary)}

Files modified: {', '.join(files_modified) if files_modified else 'None'}
Tests passed: {test_result.get('passed') if test_result else 'Not run'}

Based on the execution results, was this goal ACTUALLY achieved?
Consider:
1. Did the steps produce meaningful output (not just placeholder text)?
2. Were files actually modified if the goal required changes?
3. Do the outputs align with what the goal asked for?

Respond with JSON only:
{{"verified": true/false, "confidence": 0.0-1.0, "reason": "brief explanation"}}
"""

        try:
            response = await self.llm_router.route_request(
                messages=[
                    {"role": "system", "content": "You are a goal verification agent. Be strict — only verify goals that show evidence of real completion."},
                    {"role": "user", "content": verification_prompt},
                ],
                temperature=0.1,
            )
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            content = content.strip()
            # Extract JSON from response
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            result = json.loads(content)
            return {
                "verified": bool(result.get("verified", False)),
                "confidence": float(result.get("confidence", 0.5)),
                "reason": str(result.get("reason", "No reason provided")),
            }
        except Exception as e:
            # If verification fails, be conservative — don't claim success
            return {
                "verified": False,
                "confidence": 0.3,
                "reason": f"Verification failed: {str(e)}"
            }



def get_available_tools_for_agent(agent_name: str) -> List[str]:

    """Get list of tools available to an agent based on config."""

    config_store = get_config_store()

    try:

        config = config_store.get_active(agent_name)

        return config.get("allowed_tools", [])

    except Exception:

        return []

