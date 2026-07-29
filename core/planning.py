"""

Agent planning and tool use capabilities.

Enables agents to plan multi-step work, use tools, and execute code safely.

"""



import json

from typing import Dict, Any, List

from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage

from core.models import get_primary_model

from core.agent_config import get_config_store

from core.sandbox import execute_in_sandbox

from tools.mcp_registry import get_registered_tools

from core.api_router import get_llm_router, _provider_temperature





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

        

        prompt = f"""

{system_prompt}



Goal: {goal}



Available tools: {', '.join(available_tools)}



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

            if tool_name and tool_name in ["editor", "shell_exec", "load_tool"]:

                if tool_name == "shell_exec":

                    code = action

                    sandbox_result = execute_in_sandbox(code)

                    result["output"] = sandbox_result

                    result["status"] = "completed"

                elif tool_name == "editor":

                    result["output"] = f"Editor action: {action}"

                    result["status"] = "completed"

                else:

                    result["output"] = f"Tool action: {action}"

                    result["status"] = "completed"

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

        

        return {

            "plan": plan,

            "results": results,

            "status": "completed",

            "completed_at": datetime.utcnow().isoformat()

        }





def get_available_tools_for_agent(agent_name: str) -> List[str]:

    """Get list of tools available to an agent based on config."""

    config_store = get_config_store()

    try:

        config = config_store.get_active(agent_name)

        return config.get("allowed_tools", [])

    except Exception:

        return []

