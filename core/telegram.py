import os
import asyncio
import time
from typing import Optional, Dict, Any, List
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.error import TelegramError
from dotenv import load_dotenv

load_dotenv()

VALID_SPEAKERS = ["SYSTEM", "DAEMON", "AUTOBOT", "ALPHA", "ALPHA_EVALUATOR", "BETA", "BETA_WORKER", "EVOLUTION", "GOVERNANCE"]


def format_council_message(speaker: str, body: str) -> str:
    """Format a message with mandatory [COUNCIL:SPEAKER] prefix."""
    if speaker not in VALID_SPEAKERS:
        raise ValueError(f"Invalid speaker: {speaker}. Must be one of {VALID_SPEAKERS}")
    return f"[COUNCIL:{speaker}] {body}"


class TelegramBot:
    """Telegram bot for council communication and notifications."""
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.bot: Optional[Bot] = None
        
        if self.bot_token:
            self.bot = Bot(token=self.bot_token)
    
    async def send_message(self, message: str, chat_id: Optional[str] = None) -> bool:
        """Send a message to the specified chat."""
        if not self.bot:
            print("[TELEGRAM] Bot not initialized - missing TELEGRAM_BOT_TOKEN")
            return False
        
        target_chat_id = chat_id or self.chat_id
        if not target_chat_id:
            print("[TELEGRAM] No chat_id provided")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=target_chat_id,
                text=message,
                parse_mode="HTML"
            )
            print(f"[TELEGRAM] Message sent to {target_chat_id}")
            return True
        except TelegramError as e:
            print(f"[TELEGRAM] Error sending message: {e}")
            return False
    
    async def send_council_status(self, status: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """Send a formatted council status message."""
        body = f"<b>🤖 Council Status Update</b>\n\n"
        body += f"<b>Status:</b> {status}\n"
        
        if details:
            body += "\n<b>Details:</b>\n"
            for key, value in details.items():
                body += f"  • {key}: {value}\n"
        
        message = format_council_message("SYSTEM", body)
        return await self.send_message(message)
    
    async def send_completion_notification(self, session_id: str, summary: Dict[str, Any], goal_id: Optional[str] = None, duration_seconds: Optional[float] = None) -> bool:
        """Send a completion notification when council finishes."""
        body = f"<b>✅ Council Task Complete</b>\n\n"
        body += f"<b>Session:</b> {session_id}\n"
        
        if goal_id:
            body += f"<b>Goal ID:</b> {goal_id}\n"
        
        if duration_seconds:
            body += f"<b>Duration:</b> {duration_seconds:.1f}s\n"
        
        body += f"<b>Loop Count:</b> {summary.get('loop_count', 'N/A')}\n"
        body += f"<b>Completed Nodes:</b> {', '.join(summary.get('completed_nodes', []))}\n"
        
        if 'messages_count' in summary:
            body += f"<b>Messages:</b> {summary['messages_count']}\n"
        
        body += "\n<i>The council has completed its task successfully.</i>"
        
        message = format_council_message("DAEMON", body)
        return await self.send_message(message)
    
    async def send_error_notification(self, error: str, context: Optional[str] = None, goal_id: Optional[str] = None) -> bool:
        """Send an error notification."""
        body = f"<b>❌ Council Error</b>\n\n"
        body += f"<b>Error:</b> {error}\n"
        
        if goal_id:
            body += f"<b>Goal ID:</b> {goal_id}\n"
        
        if context:
            body += f"\n<b>Context:</b> {context}\n"
        
        message = format_council_message("SYSTEM", body)
        return await self.send_message(message)
    
    async def send_goal_progress(self, goal_id: str, status: str, details: Optional[Dict[str, Any]] = None, speaker: str = "DAEMON") -> bool:
        """Send goal progress notification."""
        body = f"<b>📊 Goal Progress</b>\n\n"
        body += f"<b>Goal ID:</b> {goal_id}\n"
        body += f"<b>Status:</b> {status}\n"
        
        if details:
            body += "\n<b>Details:</b>\n"
            for key, value in details.items():
                body += f"  • {key}: {value}\n"
        
        message = format_council_message(speaker, body)
        return await self.send_message(message)
    
    async def send_mutation_notification(self, mutation_id: str, status: str, agent_name: Optional[str] = None, speaker: str = "EVOLUTION", mutation: Optional[Dict[str, Any]] = None) -> bool:
        """Send mutation status notification."""
        body = f"<b>🧬 Mutation {status}</b>\n\n"
        body += f"<b>Mutation ID:</b> <code>{mutation_id}</code>\n"

        if agent_name:
            body += f"<b>Agent:</b> {agent_name}\n"

        if mutation:
            body += f"<b>Description:</b> {mutation.get('description', 'N/A')}\n"
            if mutation.get('rationale'):
                body += f"<b>Rationale:</b> {mutation.get('rationale', 'N/A')[:220]}\n"
            if mutation.get('mutation_type'):
                body += f"<b>Type:</b> {mutation['mutation_type']}\n"
            if mutation.get('risk_level'):
                body += f"<b>Risk Level:</b> {mutation['risk_level']}\n"
            if mutation.get('mission_pillar'):
                body += f"<b>Mission Pillar:</b> {mutation.get('mission_pillar')}\n"
            if mutation.get('mission_description'):
                body += f"<b>Mission Alignment:</b> {mutation['mission_description'][:120]}\n"
            if mutation.get('quality_score'):
                body += f"<b>Quality Score:</b> {mutation['quality_score']}\n"
            if mutation.get('status'):
                body += f"<b>Status:</b> {mutation['status']}\n"
            if mutation.get('approved_by'):
                body += f"<b>Approved By:</b> {mutation['approved_by']}\n"
            if mutation.get('approval_timestamp'):
                body += f"<b>Approved At:</b> {mutation['approval_timestamp']}\n"

            proposed_changes = mutation.get('proposed_changes') or {}
            if proposed_changes:
                summary_parts = []
                file_changes = proposed_changes.get('file_changes')
                if isinstance(file_changes, list):
                    for fc in file_changes[:3]:
                        if isinstance(fc, dict):
                            path = fc.get('path', '?')
                            kind = fc.get('kind', '?')
                            summary_parts.append(f"{kind} {path}")
                if not summary_parts:
                    for key in list(proposed_changes.keys())[:5]:
                        if key != 'file_changes':
                            summary_parts.append(f"{key}={proposed_changes[key]}")
                if summary_parts:
                    body += f"<b>Changes:</b> {', '.join(summary_parts)}\n"

            votes = mutation.get('votes') or {}
            if votes:
                vote_lines = []
                consensus = "pending"
                for voter, detail in votes.items():
                    vote = detail.get('vote', '?') if isinstance(detail, dict) else str(detail)
                    reason = detail.get('reason', '') if isinstance(detail, dict) else ''
                    vote_lines.append(f"{voter}: {vote}" + (f" — {reason[:80]}" if reason else ""))
                    if vote == 'approve':
                        consensus = 'approved'
                body += f"\n<b>Council Votes:</b> {consensus}\n"
                for line in vote_lines:
                    body += f"• {line}\n"

            if mutation.get('implementation_result'):
                result = mutation['implementation_result']
                if isinstance(result, dict):
                    if result.get('success'):
                        body += f"<b>Implementation:</b> ✅ Success\n"
                    else:
                        body += f"<b>Implementation:</b> ❌ Failed\n"
                    if result.get('error'):
                        body += f"<b>Error:</b> {str(result['error'])[:220]}\n"
                    verification = result.get('verification')
                    if isinstance(verification, dict):
                        v_success = verification.get('success')
                        v_reason = verification.get('reason', '')
                        v_metrics = verification.get('metrics', {})
                        body += f"<b>Verified:</b> {'✅' if v_success else '❌'} {v_reason}\n"
                        if v_metrics:
                            score_change = v_metrics.get('score_change', 0)
                            body += f"<b>Score Change:</b> {score_change:+.2f}\n"
                            tests_passed = v_metrics.get('tests_passed', False)
                            body += f"<b>Tests Passed:</b> {'✅' if tests_passed else '❌'}\n"
                    test_result = result.get('tests')
                    if isinstance(test_result, dict):
                        body += f"<b>Tests:</b> {'✅ Passed' if test_result.get('passed') else '❌ Failed'}\n"
                        errors = test_result.get('errors', '')
                        if errors:
                            body += f"<b>Test Errors:</b> {errors[:200]}\n"
                    metrics = result.get('metrics')
                    if isinstance(metrics, dict):
                        deltas = metrics.get('deltas', {})
                        if deltas:
                            body += f"<b>Metrics:</b> score={deltas.get('current_score', 0):.3f} (was {deltas.get('baseline', 0):.3f})\n"

                    commit_hash = result.get('commit_hash')
                    branch = result.get('branch')
                    merged = result.get('merged_to_main')
                    if commit_hash or branch:
                        body += f"\n<b>Git Proof</b>\n"
                        if branch:
                            body += f"<b>Branch:</b> <code>{branch}</code>\n"
                        if commit_hash:
                            body += f"<b>Commit:</b> <code>{commit_hash}</code>\n"
                            body += f"Verify: <code>git show {commit_hash}</code>\n"
                        if merged is not None:
                            body += f"<b>Merged:</b> {'✅ Yes' if merged else '❌ No'}\n"

        message = format_council_message(speaker, body)
        return await self.send_message(message)


class TelegramCommandListener:
    """Inbound Telegram command listener for operator control."""
    
    def __init__(self, bot_token: Optional[str] = None, allowed_chat_id: Optional[str] = None, allowed_user_ids: Optional[List[str]] = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.allowed_chat_id = allowed_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        allowed_ids_str = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
        self.allowed_user_ids = allowed_user_ids or [uid.strip() for uid in allowed_ids_str.split(",") if uid.strip()]
        
        self.start_time = time.time()
        
        self.on_create_goal = None
        self.on_get_status = None
        self.on_approve_mutation = None
        self.on_reject_mutation = None
        self.on_stop_autonomy = None
        
        if self.bot_token:
            self.app = Application.builder().token(self.bot_token).build()
            self._register_handlers()
        else:
            self.app = None
    
    def _register_handlers(self):
        """Register command handlers."""
        self.app.add_handler(CommandHandler("who", self._cmd_who))
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(CommandHandler("goal", self._cmd_goal))
        self.app.add_handler(CommandHandler("approve", self._cmd_approve))
        self.app.add_handler(CommandHandler("reject", self._cmd_reject))
        self.app.add_handler(CommandHandler("stop", self._cmd_stop))
        self.app.add_handler(CommandHandler("help", self._cmd_help))
        self.app.add_handler(CommandHandler("reload", self._cmd_reload))
        
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_plain_text))
    
    def _is_authorized(self, update: Update) -> bool:
        """Check if the message is from an authorized source."""
        if self.allowed_chat_id and str(update.effective_chat.id) != self.allowed_chat_id:
            return False
        
        if self.allowed_user_ids and str(update.effective_user.id) not in self.allowed_user_ids:
            return False
        
        return True
    
    async def _cmd_who(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Prove identity - show uptime and PID."""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized")
            return
        
        import os
        uptime = time.time() - self.start_time
        pid = os.getpid()
        
        body = f"<b>🤖 Council Identity Proof</b>\n\n"
        body += f"<b>PID:</b> {pid}\n"
        body += f"<b>Uptime:</b> {uptime:.0f}s\n"
        body += f"<b>I am the real council process.</b>"
        
        message = format_council_message("DAEMON", body)
        await update.message.reply_text(message, parse_mode="HTML")
    
    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current goals, loops, mutations."""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized")
            return
        
        if self.on_get_status:
            status = await self.on_get_status()
            body = f"<b>📊 Council Status</b>\n\n{status}"
            message = format_council_message("DAEMON", body)
            await update.message.reply_text(message, parse_mode="HTML")
        else:
            body = "Status system not yet implemented."
            message = format_council_message("DAEMON", body)
            await update.message.reply_text(message, parse_mode="HTML")
    
    async def _cmd_goal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create a real goal and queue it."""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized")
            return
        
        goal_description = " ".join(context.args) if context.args else ""
        
        if not goal_description:
            await update.message.reply_text("Usage: /goal <description>")
            return
        
        if self.on_create_goal:
            goal_id = await self.on_create_goal(goal_description, source="human")
            body = f"<b>✅ Goal Queued</b>\n\n<b>Goal ID:</b> {goal_id}\n<b>Description:</b> {goal_description}"
            message = format_council_message("DAEMON", body)
            await update.message.reply_text(message, parse_mode="HTML")
        else:
            body = "Goal system not yet implemented."
            message = format_council_message("DAEMON", body)
            await update.message.reply_text(message, parse_mode="HTML")
    
    async def _cmd_approve(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Approve a pending mutation."""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized")
            return
        
        mutation_id = context.args[0] if context.args else ""
        
        if not mutation_id:
            await update.message.reply_text("Usage: /approve <mutation_id>")
            return
        
        if self.on_approve_mutation:
            success = await self.on_approve_mutation(mutation_id, approved_by="human_telegram")
            if success:
                body = f"<b>✅ Mutation Approved</b>\n\n<b>Mutation ID:</b> {mutation_id}"
                message = format_council_message("GOVERNANCE", body)
                await update.message.reply_text(message, parse_mode="HTML")
            else:
                body = f"<b>❌ Approval Failed</b>\n\n<b>Mutation ID:</b> {mutation_id}"
                message = format_council_message("GOVERNANCE", body)
                await update.message.reply_text(message, parse_mode="HTML")
        else:
            body = "Evolution system not yet implemented."
            message = format_council_message("GOVERNANCE", body)
            await update.message.reply_text(message, parse_mode="HTML")
    
    async def _cmd_reject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reject a mutation."""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized")
            return
        
        mutation_id = context.args[0] if context.args else ""
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
        
        if not mutation_id:
            await update.message.reply_text("Usage: /reject <mutation_id> [reason]")
            return
        
        if self.on_reject_mutation:
            success = await self.on_reject_mutation(mutation_id, reason, rejected_by="human_telegram")
            if success:
                body = f"<b>❌ Mutation Rejected</b>\n\n<b>Mutation ID:</b> {mutation_id}\n<b>Reason:</b> {reason}"
                message = format_council_message("GOVERNANCE", body)
                await update.message.reply_text(message, parse_mode="HTML")
            else:
                body = f"<b>❌ Rejection Failed</b>\n\n<b>Mutation ID:</b> {mutation_id}"
                message = format_council_message("GOVERNANCE", body)
                await update.message.reply_text(message, parse_mode="HTML")
        else:
            body = "Evolution system not yet implemented."
            message = format_council_message("GOVERNANCE", body)
            await update.message.reply_text(message, parse_mode="HTML")
    
    async def _cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pause high-risk autonomous actions."""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized")
            return
        
        if self.on_stop_autonomy:
            await self.on_stop_autonomy()
            body = "<b>⏸️ Autonomy Paused</b>\n\nHigh-risk autonomous actions have been paused."
            message = format_council_message("DAEMON", body)
            await update.message.reply_text(message, parse_mode="HTML")
        else:
            body = "Autonomy control not yet implemented."
            message = format_council_message("DAEMON", body)
            await update.message.reply_text(message, parse_mode="HTML")
    
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show available commands."""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized")
            return
        
        body = """<b>📖 Council Commands</b>

<code>/who</code> - Prove identity (uptime, PID)
<code>/status</code> - Show current goals, loops, mutations
<code>/goal &lt;description&gt;</code> - Create a real goal
<code>/approve &lt;mutation_id&gt;</code> - Approve a mutation
<code>/reject &lt;mutation_id&gt; [reason]</code> - Reject a mutation
<code>/stop</code> - Pause high-risk autonomous actions
<code>/help</code> - Show this help

<b>💬 Plain Language Commands</b>
You can also use natural language:
• "Create a goal to..." or "I want to..."
• "What's the status?" or "Show status"
• "Approve mutation [id]"
• "Reject mutation [id]"
• "Stop" or "Pause"

All messages from the council use [COUNCIL:SPEAKER] prefix."""
        
        message = format_council_message("SYSTEM", body)
        await update.message.reply_text(message, parse_mode="HTML")
    
    def _classify_intent(self, text: str) -> tuple[str, str]:
        """Classify plain text intent using keyword matching.
        
        Returns: (intent, extracted_data)
        """
        text_lower = text.lower().strip()
        
        # Goal creation patterns
        goal_patterns = [
            "create a goal", "create goal", "new goal", "i want to",
            "i need to", "let's create", "please create", "add a goal",
            "add goal", "make a goal", "task:", "goal:"
        ]
        if any(pattern in text_lower for pattern in goal_patterns):
            # Extract goal description (remove common prefixes)
            goal_text = text
            for pattern in ["create a goal to", "create goal to", "new goal to", 
                          "i want to", "i need to", "let's create", "please create",
                          "add a goal to", "add goal to", "make a goal to",
                          "task:", "goal:"]:
                if pattern in text_lower:
                    idx = text_lower.find(pattern)
                    goal_text = text[idx + len(pattern):].strip()
                    break
            return ("create_goal", goal_text)
        
        # Status check patterns
        status_patterns = [
            "what's the status", "whats the status", "show status",
            "status", "current status", "how's it going", "hows it going",
            "what's happening", "whats happening", "show me the status",
            "operational", "is it running", "are you up", "health",
            "is the system up", "system operational", "are you operational",
            "is the council running", "daemon status"
        ]
        if any(pattern in text_lower for pattern in status_patterns):
            return ("check_status", "")
        
        # Approval patterns
        if "approve" in text_lower and "mutation" in text_lower:
            # Try to extract mutation ID
            words = text.split()
            for i, word in enumerate(words):
                if word.lower() == "mutation" and i + 1 < len(words):
                    return ("approve_mutation", words[i + 1].strip())
            return ("approve_mutation", "")
        
        # Rejection patterns
        if "reject" in text_lower and "mutation" in text_lower:
            words = text.split()
            for i, word in enumerate(words):
                if word.lower() == "mutation" and i + 1 < len(words):
                    return ("reject_mutation", words[i + 1].strip())
            return ("reject_mutation", "")
        
        # Stop/pause patterns
        stop_patterns = ["stop", "pause", "halt", "freeze"]
        if any(pattern == text_lower for pattern in stop_patterns):
            return ("stop", "")
        
        return ("other", "")
    
    async def _cmd_reload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Hot-reload all project modules without daemon restart."""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized")
            return
        
        await update.message.reply_text("🔄 Reloading modules...")
        
        try:
            from core.hot_reload import reload_all_project_modules, verify_reload_health
            result = reload_all_project_modules()
            healthy, health_err = verify_reload_health()
            
            reloaded_count = len(result["reloaded"])
            failed_count = len(result["failed"])
            
            if result["success"] and healthy:
                body = "<b>✅ Hot Reload Complete</b>\n\n"
                body += f"<b>Reloaded:</b> {reloaded_count} modules\n"
                if result["skipped"]:
                    body += f"<b>Skipped:</b> {len(result['skipped'])} (stateful)\n"
                body += "<i>All modules updated without restart.</i>"
            else:
                body = "<b>⚠️ Hot Reload Partial</b>\n\n"
                body += f"<b>Reloaded:</b> {reloaded_count}\n"
                body += f"<b>Failed:</b> {failed_count}\n"
                if health_err:
                    body += f"<b>Health:</b> {health_err}\n"
                for fail in result["failed"][:3]:
                    body += f"\n• {fail['module']}: {fail['error'][:80]}"
            
            message = format_council_message("DAEMON", body)
            await update.message.reply_text(message, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"❌ Reload failed: {e}")

    async def _handle_plain_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle plain text messages using NLP intent classification."""
        if not self._is_authorized(update):
            await update.message.reply_text("❌ Unauthorized")
            return
        
        message_text = update.message.text
        intent, extracted_data = self._classify_intent(message_text)
        
        if intent == "create_goal":
            if self.on_create_goal and extracted_data:
                goal_id = await self.on_create_goal(extracted_data, source="human")
                body = f"<b>✅ Goal Queued</b>\n\n<b>Goal ID:</b> {goal_id}\n<b>Description:</b> {extracted_data}"
                message = format_council_message("DAEMON", body)
                await update.message.reply_text(message, parse_mode="HTML")
            else:
                await update.message.reply_text("I understood you want to create a goal, but the goal system isn't ready yet.")
        
        elif intent == "check_status":
            if self.on_get_status:
                status = await self.on_get_status()
                body = f"<b>📊 Council Status</b>\n\n{status}"
                message = format_council_message("DAEMON", body)
                await update.message.reply_text(message, parse_mode="HTML")
            else:
                await update.message.reply_text("Status system not yet implemented.")
        
        elif intent == "approve_mutation":
            if extracted_data and self.on_approve_mutation:
                success = await self.on_approve_mutation(extracted_data, approved_by="human_telegram")
                if success:
                    body = f"<b>✅ Mutation Approved</b>\n\n<b>Mutation ID:</b> {extracted_data}"
                    message = format_council_message("GOVERNANCE", body)
                    await update.message.reply_text(message, parse_mode="HTML")
                else:
                    body = f"<b>❌ Approval Failed</b>\n\n<b>Mutation ID:</b> {extracted_data}"
                    message = format_council_message("GOVERNANCE", body)
                    await update.message.reply_text(message, parse_mode="HTML")
            else:
                await update.message.reply_text("Please specify which mutation to approve: 'approve mutation [id]'")
        
        elif intent == "reject_mutation":
            if extracted_data and self.on_reject_mutation:
                success = await self.on_reject_mutation(extracted_data, "Rejected via plain language", rejected_by="human_telegram")
                if success:
                    body = f"<b>❌ Mutation Rejected</b>\n\n<b>Mutation ID:</b> {extracted_data}"
                    message = format_council_message("GOVERNANCE", body)
                    await update.message.reply_text(message, parse_mode="HTML")
                else:
                    body = f"<b>❌ Rejection Failed</b>\n\n<b>Mutation ID:</b> {extracted_data}"
                    message = format_council_message("GOVERNANCE", body)
                    await update.message.reply_text(message, parse_mode="HTML")
            else:
                await update.message.reply_text("Please specify which mutation to reject: 'reject mutation [id]'")
        
        elif intent == "stop":
            if self.on_stop_autonomy:
                await self.on_stop_autonomy()
                body = "<b>⏸️ Autonomy Paused</b>\n\nHigh-risk autonomous actions have been paused."
                message = format_council_message("DAEMON", body)
                await update.message.reply_text(message, parse_mode="HTML")
            else:
                await update.message.reply_text("Autonomy control not yet implemented.")
        
        else:
            question = message_text.strip()
            if not question:
                body = "Send me a question or use /help for commands."
                message = format_council_message("SYSTEM", body)
                await update.message.reply_text(message, parse_mode="HTML")
                return

            try:
                from core.api_router import get_llm_router
                from core.agent_context import inject_mission_context
                from core.memory import get_persistent_memory

                router = get_llm_router()
                memory = get_persistent_memory()
                memory_context = memory.get_memory_summary("autobot", max_chars=1500)

                base_prompt = (
                    "You are the Autonomous Agent Council — a self-evolving AI system. "
                    "You are speaking directly to your human operator via Telegram. "
                    "Answer as yourself — the council — with full awareness of your mission, "
                    "capabilities, and current state. Be conversational but precise. "
                    "If you do not know something, say so plainly. "
                    "Do not invent completions or claim actions finished unless they are."
                )
                system_content = inject_mission_context(base_prompt)
                if memory_context:
                    system_content += "\n\n## Your Recent Memory\n" + memory_context

                response = await router.route_request(
                    messages=[
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": question},
                    ],
                    temperature=0.3,
                    max_tokens=800,
                )
                answer = (
                    response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "I couldn't answer that right now.")
                )
                body = f"<b>🤖 Council Answer</b>\n\n{answer}"
            except Exception as exc:
                body = f"<b>⚠️ Council Q&A Unavailable</b>\n\nReason: {exc}"

            message = format_council_message("AUTOBOT", body)
            await update.message.reply_text(message, parse_mode="HTML")
    
    async def run_polling(self):
        """Start polling for commands."""
        if self.app:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            print("[TELEGRAM] Command listener started")
        else:
            print("[TELEGRAM] Cannot start listener - bot not initialized")


# Global instances
_telegram_bot: Optional[TelegramBot] = None
_command_listener: Optional[TelegramCommandListener] = None


def get_telegram_bot() -> TelegramBot:
    """Get or create the global Telegram bot instance."""
    global _telegram_bot
    if _telegram_bot is None:
        _telegram_bot = TelegramBot()
    return _telegram_bot


def get_command_listener() -> TelegramCommandListener:
    """Get or create the global command listener instance."""
    global _command_listener
    if _command_listener is None:
        _command_listener = TelegramCommandListener()
    return _command_listener


async def send_telegram_message(message: str, chat_id: Optional[str] = None) -> bool:
    """Convenience function to send a Telegram message."""
    bot = get_telegram_bot()
    return await bot.send_message(message, chat_id)


async def send_council_message(speaker: str, body: str, chat_id: Optional[str] = None) -> bool:
    """Send a properly formatted council message with identity prefix."""
    message = format_council_message(speaker, body)
    bot = get_telegram_bot()
    return await bot.send_message(message, chat_id)


async def notify_council_completion(session_id: str, summary: Dict[str, Any], goal_id: Optional[str] = None, duration_seconds: Optional[float] = None) -> bool:
    """Notify via Telegram that the council has completed."""
    bot = get_telegram_bot()
    return await bot.send_completion_notification(session_id, summary, goal_id, duration_seconds)


async def notify_council_error(error: str, context: Optional[str] = None, goal_id: Optional[str] = None) -> bool:
    """Notify via Telegram that an error occurred."""
    bot = get_telegram_bot()
    return await bot.send_error_notification(error, context, goal_id)
