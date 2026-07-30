import asyncio

import json

import os

import time

from datetime import datetime

from typing import Dict, Any, List, Optional

from pathlib import Path



from core.curiosity import get_curiosity_engine, should_agent_explore, get_exploration_target

from core.feedback import get_feedback_loop, get_agent_performance

from core.evolution import get_evolution_engine, propose_mutation, MutationType, MutationStatus

from core.communication import get_agent_communication, send_message

from core.data_logger import log_trajectory, get_trajectories

from core.mutation_proposer import propose_mutation as propose_mutation_from_performance

from core.mutation_deduplicator import get_deduplicator

from core.snapdeploy import SnapDeployManager

from core.telegram import get_telegram_bot, send_council_message

from core.goals import get_goal_store, GoalStatus

from core.planning import AgentPlanner

from core.governor import get_governor
from core.memory import get_persistent_memory

from governance.audit_log import log_event





def calculate_reward(feedback=None):

    """Calculate goal reward from feedback."""

    

    if feedback is None:

        # Default: neutral

        return 0.5

    

    # If feedback has success rate, use it

    success_rate = feedback.get("success_rate", 0.5)

    

    # If feedback has time bonus (faster = better)

    speed_bonus = feedback.get("speed_bonus", 0.0)

    

    # Combine: 70% from success, 30% from speed

    reward = (success_rate * 0.7) + (speed_bonus * 0.3)

    

    # Ensure it's in valid range

    reward = max(0.0, min(1.0, reward))

    

    return reward





def _is_notify_worthy(proposal: Dict[str, Any]) -> bool:

    """Return True if this proposal should trigger a Telegram mutation notification."""

    if os.getenv("MUTATION_NOTIFY_PARAMS", "false").lower() == "true":

        return True

    changes = proposal.get("proposed_changes") or {}

    if isinstance(changes, dict) and changes.get("file_changes"):

        return True

    mutation_type = str(proposal.get("mutation_type", "")).lower()

    if mutation_type in {"tool_addition", "strategy_evolution", "prompt_optimization", "behavior_change"}:

        return True

    return False



class AutonomousAgentLoop:

    def __init__(self, agent_name: str, cycle_interval: int = 60):

        self.agent_name = agent_name

        self.cycle_interval = cycle_interval

        self.running = False

        self.cycle_count = 0

        self.start_time = datetime.utcnow()

        self._last_evolution_cycle = -10

        self._evolution_cycle_interval = 20

        self._last_architecture_review = -20

        

        self.curiosity_engine = get_curiosity_engine(agent_name)

        self.feedback_loop = get_feedback_loop()

        self.evolution_engine = get_evolution_engine()

        self.communication = get_agent_communication(agent_name)

        self.snapdeploy = SnapDeployManager()

        self.telegram = get_telegram_bot()

        self.goal_store = get_goal_store()

        self.planner = AgentPlanner(agent_name)

        self.governor = get_governor()

        self.memory = get_persistent_memory()

        

        self.loop_dir = Path("autonomous_loops") / agent_name

        self.loop_dir.mkdir(parents=True, exist_ok=True)

        self.last_execution = {

            "goal_id": None,

            "description": None,

            "target": None,

            "phase": None,

            "reward": None,

            "status": None,

        }

    

    async def start(self):

        self.running = True

        self.start_time = datetime.utcnow()

        print(f"[{self.agent_name.upper()}] Autonomous loop started")

        

        await send_council_message(

            self.agent_name.upper(),

            f"<b>🤖 Autonomous Loop Started</b>\n\n"

            f"<b>Agent:</b> {self.agent_name}\n"

            f"<b>Cycle Interval:</b> {self.cycle_interval}s\n"

            f"<b>Start Time:</b> {self.start_time.isoformat()}"

        )

        

        while self.running:

            try:

                await self.run_cycle()

                self.cycle_count += 1

                await asyncio.sleep(self.cycle_interval)

            except Exception as e:

                print(f"[{self.agent_name.upper()}] Error in cycle: {e}")

                await send_council_message(

                    "SYSTEM",

                    f"<b>❌ Loop Error</b>\n\n"

                    f"<b>Agent:</b> {self.agent_name}\n"

                    f"<b>Error:</b> {str(e)}",

                )

                await asyncio.sleep(10)

    

    async def stop(self):

        self.running = False

        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        print(f"[{self.agent_name.upper()}] Autonomous loop stopped after {self.cycle_count} cycles")

        

        await send_council_message(

            self.agent_name.upper(),

            f"<b>⏹️ Autonomous Loop Stopped</b>\n\n"

            f"<b>Agent:</b> {self.agent_name}\n"

            f"<b>Total Cycles:</b> {self.cycle_count}\n"

            f"<b>Uptime:</b> {uptime:.0f}s"

        )

    

    async def run_cycle(self):

        # Check resource limits before running

        if not self.governor.can_run_cycle():

            print(f"  [{self.agent_name.upper()}] Resource limit reached, skipping cycle")

            await asyncio.sleep(self.cycle_interval)

            return

        

        cycle_start = datetime.utcnow()

        cycle_id = f"cycle_{self.agent_name}_{self.cycle_count + 1}"

        print(f"\n[{self.agent_name.upper()}] === Cycle {self.cycle_count + 1} ===")

        

        performance = get_agent_performance(self.agent_name)

        curiosity_score = self.curiosity_engine.calculate_curiosity_score()

        

        print(f"  Performance: {performance.get('success_rate', 0):.2f}")

        print(f"  Curiosity: {curiosity_score:.2f}")

        

        # Select and execute a goal

        await self._select_and_execute_goal(cycle_id, cycle_start)

        

        if (performance.get("trend") == "declining" or performance.get("success_rate", 0) < 0.4) and (self.cycle_count - self._last_evolution_cycle) >= self._evolution_cycle_interval:

            self._last_evolution_cycle = self.cycle_count

            await self._trigger_evolution(performance, cycle_id)

        

        if self.cycle_count % 15 == 0 and (self.cycle_count - self._last_architecture_review) >= 15:

            self._last_architecture_review = self.cycle_count

            await self._review_architecture(cycle_id)

        

        if should_agent_explore(self.agent_name):

            await self._explore(cycle_id)

        

        if performance.get("total_trajectories", 0) > 10:

            await self._consider_spawning(cycle_id)

        

        await self._check_messages()

        

        cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()

        print(f"  Cycle completed in {cycle_duration:.2f}s")

        

        self._log_cycle(performance, curiosity_score, cycle_duration, cycle_id)

        
        # Store cycle result in persistent memory for cross-session recall
        try:
            self.memory.store_cycle_result(
                agent_name=self.agent_name,
                cycle_count=self.cycle_count,
                goal_id=self.last_execution.get("goal_id"),
                status=self.last_execution.get("status", "unknown"),
                reward=self.last_execution.get("reward"),
                phase=self.last_execution.get("phase"),
            )
        except Exception as e:
            print(f"  [{self.agent_name.upper()}] Memory store error: {e}")

    

    async def _review_architecture(self, cycle_id: str = None):

        print(f"  [{self.agent_name.upper()}] Reviewing architecture and mission progress")

        

        recent_goals = self.goal_store.get_recent_goals(limit=20, agent_name=self.agent_name)

        failed_goals = [g for g in recent_goals if g.get("status") == "failed"]

        

        if len(failed_goals) >= 2:

            await self._trigger_architecture_evolution(failed_goals, cycle_id)

        

        if self.cycle_count % 30 == 0:

            await self._propose_architecture_improvement(cycle_id)

    

    async def _trigger_architecture_evolution(self, failed_goals, cycle_id: str = None):

        from core.evolution import MutationType, propose_mutation

        

        performance = {

            "success_rate": max(0.0, 1.0 - (len(failed_goals) / max(1, len(self.goal_store.get_recent_goals(limit=20, agent_name=self.agent_name))))),

            "recent_failures": len(failed_goals),

            "trend": "declining" if len(failed_goals) >= 3 else "stable"

        }

        

        recent_trajectories = []

        try:

            for entry in get_trajectories(agent_name=self.agent_name, limit=20):

                prompt = entry.get("prompt", "")

                response = entry.get("response", "")

                if prompt or response:

                    recent_trajectories.append(f"{prompt} | {response}")

        except Exception:

            pass

        

        council_discussion = self._load_discussion_summary()

        learned_context = self._build_learning_context()



        proposal = await propose_mutation_from_performance(

            agent_name=self.agent_name,

            performance=performance,

            recent_trajectories=recent_trajectories or None,

            council_discussion=council_discussion,

            learned_context=learned_context,

        )

        

        if not proposal:

            return

        

        proposal_for_dedup = {

            "agent_name": self.agent_name,

            "mutation_type": proposal.get("mutation_type", "parameter_adjustment"),

            "description": proposal.get("description", ""),

            "proposed_changes": proposal.get("proposed_changes", {}),

        }

        if not get_deduplicator().should_propose(proposal_for_dedup):

            print(f"  [{self.agent_name.upper()}] Architecture evolution duplicate skipped")

            return

        

        mutation_type_str = proposal.get("mutation_type", "parameter_adjustment")

        try:

            mutation_type = MutationType(mutation_type_str)

        except ValueError:

            mutation_type = MutationType.STRATEGY_EVOLUTION

        

        mutation = propose_mutation(

            agent_name=self.agent_name,

            mutation_type=mutation_type,

            description=proposal.get("description", "Architecture improvement"),

            rationale=proposal.get("rationale", f"Resolve {len(failed_goals)} recent failures"),

            proposed_changes=proposal.get("proposed_changes", {}),

            expected_improvement=float(proposal.get("expected_improvement", 0.2)),

            risk_level="medium"

        )

        

        print(f"  Architecture mutation proposed: {mutation.mutation_id}")

        

        if _is_notify_worthy(proposal):

            await send_council_message(

                "EVOLUTION",

                f"<b>🧱 Architecture Review Mutation</b>\n\n"

                f"<b>Mutation ID:</b> {mutation.mutation_id}\n"

                f"<b>Description:</b> {proposal.get('description', 'Architecture improvement')}\n"

                f"<b>Failures:</b> {len(failed_goals)} recent failures\n"

                f"<b>Agent:</b> {self.agent_name}"

            )

    

    async def _propose_architecture_improvement(self, cycle_id: str = None):

        from core.evolution import MutationType, propose_mutation

        import asyncio

        

        performance = get_agent_performance(self.agent_name)

        performance["requesting_architecture_improvement"] = True

        

        recent_trajectories = []

        try:

            for entry in get_trajectories(agent_name=self.agent_name, limit=20):

                prompt = entry.get("prompt", "")

                response = entry.get("response", "")

                if prompt or response:

                    recent_trajectories.append(f"{prompt} | {response}")

        except Exception:

            pass

        

        council_discussion = self._load_discussion_summary()

        learned_context = self._build_learning_context()

        

        proposal = await propose_mutation_from_performance(

            agent_name=self.agent_name,

            performance=performance,

            recent_trajectories=recent_trajectories or None,

            council_discussion=council_discussion,

            learned_context=learned_context,

        )

        

        if not proposal:

            return

        

        proposal_for_dedup = {

            "agent_name": self.agent_name,

            "mutation_type": proposal.get("mutation_type", "parameter_adjustment"),

            "description": proposal.get("description", ""),

            "proposed_changes": proposal.get("proposed_changes", {}),

        }

        if not get_deduplicator().should_propose(proposal_for_dedup):

            print(f"  [{self.agent_name.upper()}] Architecture improvement duplicate skipped")

            return

        

        mutation_type_str = proposal.get("mutation_type", "strategy_evolution")

        try:

            mutation_type = MutationType(mutation_type_str)

        except ValueError:

            mutation_type = MutationType.STRATEGY_EVOLUTION

        

        if mutation_type not in (MutationType.TOOL_ADDITION, MutationType.STRATEGY_EVOLUTION, MutationType.BEHAVIOR_CHANGE):

            mutation_type = MutationType.STRATEGY_EVOLUTION

        

        mutation = propose_mutation(

            agent_name=self.agent_name,

            mutation_type=mutation_type,

            description=proposal.get("description", "Architecture improvement"),

            rationale=proposal.get("rationale", "Mission-aligned architecture improvement"),

            proposed_changes=proposal.get("proposed_changes", {}),

            expected_improvement=float(proposal.get("expected_improvement", 0.1)),

            risk_level="medium"

        )

        

        print(f"  Architecture improvement proposed: {mutation.mutation_id}")

        

        if _is_notify_worthy(proposal):

            await send_council_message(

                "EVOLUTION",

                f"<b>🚀 Architecture Improvement Proposed</b>\n\n"

                f"<b>Mutation ID:</b> {mutation.mutation_id}\n"

                f"<b>Description:</b> {proposal.get('description', 'Architecture improvement')}\n"

                f"<b>Agent:</b> {self.agent_name}"

            )

    

    async def _select_and_execute_goal(self, cycle_id: str = None, cycle_start: datetime = None):

        """Select highest-priority pending goal and execute it using planning."""

        pending_goals = self.goal_store.get_pending_goals(limit=1)

        if not pending_goals:
            print(f"  [{self.agent_name.upper()}] No pending goals — skipping goal execution")
            return


        goal = pending_goals[0]

        goal = pending_goals[0]

        goal_id = goal["goal_id"]

        

        print(f"  [{self.agent_name.upper()}] Executing goal {goal_id[:12]}...: {goal['description'][:50]}")

        

        self.last_execution = {

            "goal_id": goal_id,

            "description": goal.get("description"),

            "target": goal.get("metadata", {}).get("target", goal.get("metadata", {}).get("type")),

            "phase": "goal_execution",

            "reward": None,

            "status": None,

        }

        

        # Assign goal to this agent

        self.goal_store.assign_goal(goal_id, self.agent_name)

        self.goal_store.update_goal_status(goal_id, GoalStatus.IN_PROGRESS.value)

        

        await send_council_message(

            self.agent_name.upper(),

            f"<b>🎯 Goal Started</b>\n\n"

            f"<b>Goal ID:</b> {goal_id}\n"

            f"<b>Description:</b> {goal['description'][:100]}\n"

            f"<b>Agent:</b> {self.agent_name}"

        )

        

        try:

            # Create a plan for the goal

            plan_result = await self.planner.create_plan(goal["description"])

            

            if plan_result.get("status") != "created":

                raise Exception(f"Failed to create plan: {plan_result.get('error')}")

            

            # Execute the plan

            execution_result = await self.planner.execute_plan(plan_result)

            

            # Calculate reward based on execution success

            if execution_result.get("status") == "completed":

                reward = calculate_reward({"success_rate": 0.9, "speed_bonus": 0.1})

            else:

                reward = calculate_reward({"success_rate": 0.1, "speed_bonus": 0.0})

            

            self.last_execution = {

                "goal_id": goal_id,

                "description": goal.get("description"),

                "target": goal.get("metadata", {}).get("target", goal.get("metadata", {}).get("type")),

                "phase": "goal_execution",

                "reward": reward,

                "status": execution_result.get("status"),

            }

            

            # Log trajectory

            log_trajectory(

                agent_name=self.agent_name,

                state={"phase": "goal_execution", "cycle_id": cycle_id, "plan_steps": len(plan_result.get("plan", {}).get("steps", []))},

                prompt=goal["description"],

                response=f"Goal executed: {goal_id}, Status: {execution_result.get('status')}",

                reward=reward,

                session_id=goal_id,

                metadata={"goal_id": goal_id, "type": "goal_execution", "execution_status": execution_result.get("status")}

            )

            

            # Update goal status

            self.goal_store.update_goal_status(

                goal_id,

                GoalStatus.COMPLETED.value if execution_result.get("status") == "completed" else GoalStatus.FAILED.value,

                result_summary=f"Executed by {self.agent_name}, Status: {execution_result.get('status')}",

                reward=reward

            )

            

            await send_council_message(

                self.agent_name.upper(),

                f"<b>✅ Goal Completed</b>\n\n"

                f"<b>Goal ID:</b> {goal_id}\n"

                f"<b>Status:</b> {execution_result.get('status')}\n"

                f"<b>Reward:</b> {reward:.2f}\n"

                f"<b>Duration:</b> {(datetime.utcnow() - cycle_start).total_seconds():.1f}s"

            )

            

        except Exception as e:

            print(f"  [{self.agent_name.upper()}] Goal execution failed: {e}")

            self.last_execution = {

                "goal_id": goal_id,

                "description": goal.get("description"),

                "target": goal.get("metadata", {}).get("target", goal.get("metadata", {}).get("type")),

                "phase": "goal_execution",

                "reward": calculate_reward({"success_rate": 0.1, "speed_bonus": 0.0}),

                "status": f"failed: {str(e)}",

            }

            self.goal_store.update_goal_status(

                goal_id,

                GoalStatus.FAILED.value,

                result_summary=f"Failed: {str(e)}"

            )

            

            await send_council_message(

                "SYSTEM",

                f"<b>❌ Goal Failed</b>\n\n"

                f"<b>Goal ID:</b> {goal_id}\n"

                f"<b>Error:</b> {str(e)}"

            )

    

    async def _trigger_evolution(self, performance: Dict[str, Any], cycle_id: str = None):

        print(f"  [{self.agent_name.upper()}] Triggering evolution due to poor performance")



        success_rate = performance.get("success_rate", 0)



        recent_trajectories = []

        try:

            for entry in get_trajectories(agent_name=self.agent_name, limit=20):

                prompt = entry.get("prompt", "")

                response = entry.get("response", "")

                if prompt or response:

                    recent_trajectories.append(f"{prompt} | {response}")

        except Exception as exc:

            print(f"  [{self.agent_name.upper()}] Failed to load trajectories: {exc}")



        mission_pillar = await self._select_mission_pillar_for_evolution()



        council_discussion = self._load_discussion_summary()

        learned_context = self._build_learning_context()



        proposal = await propose_mutation_from_performance(

            agent_name=self.agent_name,

            performance=performance,

            recent_trajectories=recent_trajectories or None,

            mission_pillar=mission_pillar,

            council_discussion=council_discussion,

            learned_context=learned_context,

        )



        if not proposal:

            print(f"  [{self.agent_name.upper()}] No meaningful mutation proposed; skipping notification/voting")

            return



        discussion_summary = await self._run_council_discussion(proposal)



        self._save_discussion_summary(discussion_summary)



        mutation_type_str = proposal.get("mutation_type", "parameter_adjustment")

        try:

            mutation_type = MutationType(mutation_type_str)

        except ValueError:

            mutation_type = MutationType.PARAMETER_ADJUSTMENT



        mutation = propose_mutation(

            agent_name=self.agent_name,

            mutation_type=mutation_type,

            description=proposal.get("description", "Auto-generated tuning"),

            rationale=proposal.get("rationale", "Performance-based proposer output"),

            proposed_changes=proposal.get("proposed_changes", {}),

            expected_improvement=float(proposal.get("expected_improvement", 0.1)),

            risk_level=proposal.get("risk_level", "medium")

        )



        print(f"  Mutation proposed: {mutation.mutation_id}")

        print(f"  Proposal: {proposal}")



        if _is_notify_worthy(proposal):

            await self.telegram.send_mutation_notification(

                mutation_id=mutation.mutation_id,

                status="PROPOSED",

                agent_name=self.agent_name,

                speaker="EVOLUTION",

                mutation=mutation.to_dict()

            )



        # Advance PROPOSED mutations to PENDING_APPROVAL if not already done
        if mutation.status == MutationStatus.PROPOSED:
            self.evolution_engine.request_approval(mutation.mutation_id)
            mutation = self.evolution_engine.get_mutation(mutation.mutation_id) or mutation

        if mutation.status == MutationStatus.PENDING_APPROVAL:

            try:

                vote_result = await self.evolution_engine.collect_council_votes(

                    mutation.mutation_id,

                    discussion_context=discussion_summary,

                )

                votes = vote_result.get("votes", {})

                if _is_notify_worthy(proposal):

                    await self.telegram.send_mutation_notification(

                        mutation_id=mutation.mutation_id,

                        status="VOTES",

                        agent_name=self.agent_name,

                        speaker="GOVERNANCE",

                        mutation={"votes": votes, "consensus": vote_result.get("consensus")}

                    )


                consensus = vote_result.get("consensus")
                print(f"  [{self.agent_name.upper()}] Council votes: {votes} -> {consensus}")

                # If approved, implement immediately
                if consensus == "approved":
                    result = self.evolution_engine.implement_mutation(mutation.mutation_id)
                    if result.get("success"):
                        print(f"  [{self.agent_name.upper()}] Mutation {mutation.mutation_id} IMPLEMENTED by council")
                    else:
                        print(f"  [{self.agent_name.upper()}] Implementation failed: {result.get(chr(39)+"error"+chr(39))}")

            except Exception as exc:

                print(f"  [{self.agent_name.upper()}] Council votes failed: {exc}")



    DISCUSSION_SUMMARY_FILE = "evolution/last_discussion_summary.txt"



    def _load_discussion_summary(self) -> Optional[str]:

        try:

            path = Path(self.DISCUSSION_SUMMARY_FILE)

            if path.exists():

                with open(path, "r") as f:

                    content = f.read().strip()

                    return content if content else None

        except Exception:

            pass

        return None



    def _save_discussion_summary(self, summary: str) -> None:

        try:

            path = Path(self.DISCUSSION_SUMMARY_FILE)

            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w") as f:

                f.write(summary)

        except Exception:

            pass



    def _build_learning_context(self) -> str:

        try:

            from core.evolution import get_evolution_engine



            engine = get_evolution_engine()

            promoted = engine.get_promoted_mutations(self.agent_name, limit=3)

            failed = engine.get_failed_mutations(self.agent_name, limit=3)



            context = "## What Worked (Promoted Mutations):\n"

            if promoted:

                for m in promoted:

                    improvement = (

                        m.implementation_result.get("improvement")

                        if isinstance(m.implementation_result, dict)

                        else None

                    )

                    context += f"✅ {m.description}"

                    if improvement:

                        context += f" — improvement: {improvement}"

                    context += "\n"

            else:

                context += "- no promoted mutations yet\n"



            context += "\n## What Failed (Rolled Back / Failed):\n"

            if failed:

                for m in failed:

                    reason = (

                        m.implementation_result.get("reason_rollback")

                        if isinstance(m.implementation_result, dict)

                        else str(m.implementation_result)

                    )

                    context += f"❌ {m.description}: {reason}\n"

            else:

                context += "- no failed mutations yet\n"



            return context

        except Exception:

            return "- unable to load learning context"



    async def _select_mission_pillar_for_evolution(self) -> int:

        try:

            from core.mutation_proposer import select_mission_pillar

            return await select_mission_pillar()

        except Exception:

            return 1



    async def _run_council_discussion(self, proposal: Dict[str, Any]) -> str:

        try:

            from core.agent_communication_enhanced import get_discussion_space

            from core.react import extract_react_parts, build_react_system_prompt

            discussion_space = get_discussion_space()

            discussion = discussion_space.open_discussion(

                topic=proposal.get("description", "evolution"),

                mutation_id=None,

            )



            council_agents = ["autobot", "alpha_evaluator", "beta_worker"]

            import json as _json
            mutation_context = (
                f"\nMUTATION DETAILS:\n"
                f"- Description: {proposal.get('description', 'N/A')}\n"
                f"- Rationale: {proposal.get('rationale', 'N/A')}\n"
                f"- Type: {proposal.get('mutation_type', 'N/A')}\n"
                f"- Changes: {_json.dumps(proposal.get('proposed_changes', {}))[:500]}\n"
                f"- Risk: {proposal.get('risk_level', 'N/A')}\n"
                f"- Expected Improvement: {proposal.get('expected_improvement', 'N/A')}\n"
            )

            discussion_prompts = [

                f"You are Autobot. Briefly assess this mutation for system integration risk (1-2 sentences).{mutation_context}",

                f"You are Alpha Evaluator. Briefly assess this mutation for safety and rationale quality (1-2 sentences).{mutation_context}",

                f"You are Beta Worker. Briefly assess this mutation for feasibility and side effects (1-2 sentences).{mutation_context}",

            ]

            system_prompts = {

                "autobot": "You are Autobot, the security auditor and orchestrator.",

                "alpha_evaluator": "You are Alpha, the mission alignment evaluator.",

                "beta_worker": "You are Beta, the feasibility evaluator and worker.",

            }



            for agent_name, prompt in zip(council_agents, discussion_prompts):

                try:

                    from core.api_router import get_llm_router

                    router = get_llm_router()

                    react_system = build_react_system_prompt(system_prompts[agent_name], agent_name)

                    response = await router.route_request(

                        messages=[

                            {"role": "system", "content": react_system},

                            {"role": "user", "content": prompt},

                        ],

                        temperature=0.2,

                    )

                    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

                    content = content.strip()

                    if content.startswith("```"):

                        content = content.split("```", 2)[1]

                        if content.startswith("json"):

                            content = content[4:]

                    reasoning, action_text = extract_react_parts(content)

                    reasoning_text = reasoning or action_text[:240]

                except Exception:

                    reasoning_text = "Review pending"



                discussion_space.agent_contributes(

                    discussion_id=discussion["id"],

                    agent_name=agent_name,

                    thoughts={"vote": "approve", "reasoning": reasoning_text},

                )



            summary = discussion_space.get_discussion_summary(discussion["id"])

            if summary:

                parts = []

                for agent, thoughts in summary.get("participants", {}).items():

                    parts.append(f"{agent}: {thoughts.get('reasoning', '')}")

                return "\n".join(parts)

        except Exception as exc:

            print(f"  [{self.agent_name.upper()}] Council discussion failed: {exc}")

        return str(proposal.get("description", ""))

    

    async def _explore(self, cycle_id: str = None):

        if self._has_unresolved_blockers():

            print(f"  [{self.agent_name.upper()}] Skipping curiosity exploration: unresolved blockers detected")

            return

        

        print(f"  [{self.agent_name.upper()}] Exploring based on curiosity")

        

        target = get_exploration_target(self.agent_name)

        

        exploration_goal_description = f"Exploration: {target['description']}"

        goal_id = self.goal_store.create_goal(

            description=exploration_goal_description,

            source="curiosity",

            priority=5,

            assigned_agent=self.agent_name,

            metadata={"type": "exploration", "target": target, "cycle_id": cycle_id}

        )

        

        print(f"  Created exploration goal {goal_id[:12]}...: {target['description']}")

        

        try:

            from core.graph import app

            

            initial_state = {

                "messages": [("user", exploration_goal_description)],

                "loop_count": 0,

                "completed_nodes": [],

                "recent_tool_invocations": [],

                "codebase_hash": "",

                "reasoning_traces": [],

                "error_feedback": [],

                "last_error_trace": None,

                "active_mutation_id": None,

                "proposed_mutation_code": None,

                "mission_rationale": exploration_goal_description,

                "council_votes": {"autobot": None, "alpha_evaluator": None, "beta_worker": None},

                "mission_scores": {"autobot": 0.0, "alpha_evaluator": 0.0, "beta_worker": 0.0},

                "operator_override": None,

                "operator_override_rationale": None,

                "operator_override_timestamp": None,

                "escalation_reason": None,

                "requires_operator_approval": False,

                "proposed_version": None,

                "current_version": "v1.0.0",

                "rollback_pending": False,

                "rollback_target_version": None,

                "rollback_approved": False,

                "rollback_reason": None,

                "last_snapshot": None,

                "saga_transactions": [],

            }

            

            config = {"configurable": {"thread_id": goal_id}}

            

            final_state = None

            async for chunk in app.astream(initial_state, config=config, stream_mode="updates"):

                for node_name, state_update in chunk.items():

                    final_state = state_update

            

            if final_state and "voting_complete" in final_state.get("completed_nodes", []):

                reward = calculate_reward({"success_rate": 0.8, "speed_bonus": 0.2})

            else:

                reward = calculate_reward({"success_rate": 0.4, "speed_bonus": 0.0})

            

            self.last_execution = {

                "goal_id": goal_id,

                "description": exploration_goal_description,

                "target": target.get("type"),

                "phase": "exploration",

                "reward": reward,

                "status": GoalStatus.COMPLETED.value if reward >= 0.7 else GoalStatus.FAILED.value,

            }

            

            log_trajectory(

                agent_name=self.agent_name,

                state={"phase": "exploration", "cycle": self.cycle_count, "cycle_id": cycle_id, "goal_id": goal_id},

                prompt=exploration_goal_description,

                response=f"Exploration executed: {goal_id}, Target: {target['type']}",

                reward=reward,

                session_id=goal_id,

                metadata={"type": "exploration", "target": target, "cycle_id": cycle_id, "goal_id": goal_id}

            )

            

            self.goal_store.update_goal_status(

                goal_id,

                GoalStatus.COMPLETED.value if reward >= 0.7 else GoalStatus.FAILED.value,

                result_summary=f"Exploration by {self.agent_name}, Target: {target['type']}, Reward: {reward:.2f}",

                reward=reward

            )

            

            print(f"  Exploration completed with real reward: {reward:.2f}")

            

        except Exception as e:

            print(f"  [{self.agent_name.upper()}] Exploration execution failed: {e}")

            self.last_execution = {

                "goal_id": goal_id,

                "description": exploration_goal_description,

                "target": target.get("type"),

                "phase": "exploration",

                "reward": calculate_reward({"success_rate": 0.1, "speed_bonus": 0.0}),

                "status": f"failed: {str(e)}",

            }

            self.goal_store.update_goal_status(

                goal_id,

                GoalStatus.FAILED.value,

                result_summary=f"Exploration failed: {str(e)}",

                reward=calculate_reward({"success_rate": 0.1, "speed_bonus": 0.0})

            )

            

            log_trajectory(

                agent_name=self.agent_name,

                state={"phase": "exploration", "cycle": self.cycle_count, "cycle_id": cycle_id, "goal_id": goal_id},

                prompt=exploration_goal_description,

                response=f"Exploration failed: {str(e)}",

                reward=calculate_reward({"success_rate": 0.1, "speed_bonus": 0.0}),

                session_id=goal_id,

                metadata={"type": "exploration", "target": target, "cycle_id": cycle_id, "goal_id": goal_id, "error": str(e)}

            )

        

        self.curiosity_engine.log_curiosity_event(

            "exploration_completed",

            {"target": target, "cycle_id": cycle_id, "goal_id": goal_id}

        )

    

    def _has_unresolved_blockers(self) -> bool:

        recent = self.goal_store.get_recent_goals(limit=5, agent_name=self.agent_name)

        failures = [g for g in recent if g.get("status") == GoalStatus.FAILED.value]

        if not failures:

            return False

        blockers = {g.get("result_summary") or g.get("description", "") for g in failures}

        return len(blockers) >= 2

    

    async def _consider_spawning(self, cycle_id: str = None):

        performance = get_agent_performance(self.agent_name)

        

        if performance.get("total_trajectories", 0) > 20:

            print(f"  [{self.agent_name.upper()}] Considering container spawning")

            

            dockerfile = self._generate_worker_dockerfile()

            

            deployment_name = f"{self.agent_name}_worker_{self.cycle_count}"

            

            print(f"  Would spawn: {deployment_name}")

            print(f"  (SnapDeploy integration ready but requires API key)")

    

    def _generate_worker_dockerfile(self) -> str:

        return f"""FROM python:3.11-slim



WORKDIR /app



COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt



COPY core/ ./core/

COPY agents/ ./agents/



ENV AGENT_NAME={self.agent_name}



CMD ["python", "-m", "agents.{self.agent_name}"]

"""

    

    async def _check_messages(self):

        messages = self.communication.receive(limit=5)

        

        for msg in messages:

            print(f"  [{self.agent_name.upper()}] Received message: {msg.message_type}")

            

            if msg.message_type == "mutation_approved":

                mutation_id = msg.content.get("mutation_id")

                if mutation_id:

                    mutation = self.evolution_engine.get_mutation(mutation_id)

                    result = None

                    if mutation and mutation.status == MutationStatus.APPROVED:

                        result = self.evolution_engine.implement_mutation(mutation_id)

                    

                    mutation = self.evolution_engine.get_mutation(mutation_id)

                    if mutation and mutation.status in (MutationStatus.PROMOTED, MutationStatus.ROLLED_BACK):

                        print(f"  Mutation {mutation.status.value}: {mutation_id}")

                        status = mutation.status.value.upper()

                        await self.telegram.send_mutation_notification(

                            mutation_id=mutation_id,

                            status=status,

                            agent_name=self.agent_name,

                            speaker="EVOLUTION",

                            mutation=mutation.to_dict()

                        )

                    elif result and not result.get("success"):

                        await self.telegram.send_mutation_notification(

                            mutation_id=mutation_id,

                            status="FAILED",

                            agent_name=self.agent_name,

                            speaker="EVOLUTION",

                            mutation={"error": result.get("error")}

                        )

        

        for mutation in self.evolution_engine.get_agent_mutations(self.agent_name):

            if mutation.rollout_state == "canary":

                completed = getattr(mutation, 'rollout_soak_completed_cycles', 0) or 0

                mutation.rollout_soak_completed_cycles = completed + 1

                self.evolution_engine._save_mutation(mutation)

                

                if mutation.rollout_soak_completed_cycles >= mutation.rollout_soak_cycles:

                    try:

                        from core.rollout import advance_rollout as _advance_rollout

                        rollout_result = _advance_rollout(mutation.mutation_id)

                        mutation = self.evolution_engine.get_mutation(mutation.mutation_id)

                        if not mutation:

                            continue

                        

                        state = mutation.rollout_state

                        if state == "complete":

                            await self.telegram.send_mutation_notification(

                                mutation_id=mutation.mutation_id,

                                status="COMPLETE",

                                agent_name=self.agent_name,

                                speaker="GOVERNANCE",

                                mutation=rollout_result

                            )

                        elif state == "failed":

                            await self.telegram.send_mutation_notification(

                                mutation_id=mutation.mutation_id,

                                status="ROLLOUT_FAILED",

                                agent_name=self.agent_name,

                                speaker="GOVERNANCE",

                                mutation=rollout_result

                            )

                        elif state == "rolling_out":

                            await self.telegram.send_mutation_notification(

                                mutation_id=mutation.mutation_id,

                                status="FLEET",

                                agent_name=self.agent_name,

                                speaker="GOVERNANCE",

                                mutation=rollout_result

                            )

                    except Exception as exc:

                        print(f"  Rollout advance failed for {mutation.mutation_id}: {exc}")

    

    def _log_cycle(self, performance: Dict, curiosity: float, duration: float, cycle_id: str = None):

        cycle_log = {

            "timestamp": datetime.utcnow().isoformat(),

            "agent": self.agent_name,

            "cycle": self.cycle_count,

            "cycle_id": cycle_id,

            "performance": performance,

            "curiosity_score": curiosity,

            "duration_seconds": duration,

            "goal_id": self.last_execution.get("goal_id"),

            "phase": self.last_execution.get("phase"),

            "target": self.last_execution.get("target"),

            "reward": self.last_execution.get("reward"),

            "execution_status": self.last_execution.get("status"),

        }

        

        log_file = self.loop_dir / f"cycle_{self.cycle_count:04d}.json"

        

        # Ensure directory exists before writing

        self.loop_dir.mkdir(parents=True, exist_ok=True)

        

        with open(log_file, "w") as f:

            json.dump(cycle_log, f, indent=2)







_council_loops: Dict[str, AutonomousAgentLoop] = {}



def get_agent_loop(agent_name: str, cycle_interval: int = 60) -> AutonomousAgentLoop:

    if agent_name not in _council_loops:

        _council_loops[agent_name] = AutonomousAgentLoop(agent_name, cycle_interval)

    return _council_loops[agent_name]



async def _maintenance_loop(cycle_interval: int = 60):
    """Background maintenance: health checks, daily reports, periodic commits."""
    import subprocess
    from core.daily_report import should_send_daily_report, send_daily_report
    from core.health_monitor import HealthMonitor

    monitor = HealthMonitor()
    cycle_count = 0

    while True:
        try:
            await asyncio.sleep(cycle_interval)
            cycle_count += 1

            # Health check every 5 cycles
            if cycle_count % 5 == 0:
                try:
                    monitor.run_all_checks()
                except Exception:
                    pass

            # Daily report check every cycle (it self-throttles to once/day)
            if cycle_count % 10 == 0:
                try:
                    if should_send_daily_report():
                        await asyncio.to_thread(send_daily_report)
                except Exception:
                    pass

            # Periodic commit every 15 cycles (~15 min) to sync runtime artifacts
            if cycle_count % 15 == 0:
                try:
                    result = await asyncio.to_thread(
                        subprocess.run,
                        ["git", "status", "--porcelain"],
                        capture_output=True, text=True, cwd="."
                    )
                    if result.stdout.strip():
                        await asyncio.to_thread(
                            subprocess.run,
                            ["git", "add", "-A"],
                            capture_output=True, cwd="."
                        )
                        await asyncio.to_thread(
                            subprocess.run,
                            ["git", "commit", "-m", "chore: sync runtime artifacts"],
                            capture_output=True, cwd="."
                        )
                        await asyncio.to_thread(
                            subprocess.run,
                            ["git", "push"],
                            capture_output=True, cwd="."
                        )
                except Exception:
                    pass

        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(cycle_interval)


async def start_council(cycle_interval: int = 60):

    agents = ["autobot", "alpha_evaluator", "beta_worker"]

    

    loops = [get_agent_loop(agent, cycle_interval) for agent in agents]

    

    tasks = [loop.start() for loop in loops]

    # Add maintenance background task
    tasks.append(_maintenance_loop(cycle_interval))

    await asyncio.gather(*tasks)



async def stop_council():

    for loop in _council_loops.values():

        await loop.stop()





if __name__ == "__main__":

    import argparse

    

    parser = argparse.ArgumentParser(description="Autonomous agent loop")

    parser.add_argument("--agent", help="Run specific agent")

    parser.add_argument("--all", action="store_true", help="Run all agents")

    parser.add_argument("--interval", type=int, default=60, help="Cycle interval in seconds")

    

    args = parser.parse_args()

    

    if args.all:

        asyncio.run(start_council(args.interval))

    elif args.agent:

        loop = get_agent_loop(args.agent, args.interval)

        asyncio.run(loop.start())

    else:

        parser.print_help()

