import os
from datetime import datetime
from typing import Dict, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from governance.decision_logger import DecisionLogger

class OperatorInterface:
    def __init__(self, bot_token: str = None, chat_id: int = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or int(os.getenv("TELEGRAM_CHAT_ID", "0"))
        self.decision_logger = DecisionLogger()
        
        if self.bot_token:
            self.app = Application.builder().token(self.bot_token).build()
            self.app.add_handler(CallbackQueryHandler(self.button_callback))
        else:
            self.app = None
            print("[OPERATOR] Warning: TELEGRAM_BOT_TOKEN not set")
    
    async def request_mutation_approval(self, mutation_id: str, proposal: Dict):
        """Send mutation decision to operator on Telegram"""
        
        if not self.app:
            print(f"[OPERATOR] Cannot send Telegram message - bot not initialized")
            return
        
        votes = proposal.get("votes", {})
        message = f"""
🔵 MUTATION READY FOR REVIEW

ID: {mutation_id}
Type: {proposal.get('type', 'unknown')}

Mission Alignment: {proposal.get('mission_rationale', 'N/A')[:100]}...

Council Votes:
{'✅' if votes.get('autobot') else '❌'} Autobot: {'APPROVE' if votes.get('autobot') else 'REJECT'}
{'✅' if votes.get('alpha_evaluator') else '❌'} Alpha: {'APPROVE' if votes.get('alpha_evaluator') else 'REJECT'}
{'✅' if votes.get('beta_worker') else '❌'} Beta: {'APPROVE' if votes.get('beta_worker') else 'REJECT'}

What would you like to do?
"""
        
        keyboard = [
            [
                InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{mutation_id}"),
                InlineKeyboardButton("⏸ HOLD", callback_data=f"hold_{mutation_id}"),
                InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{mutation_id}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.app.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            reply_markup=reply_markup
        )
    
    async def request_rollback_approval(self, mutation_id: str, current_version: str, 
                                       target_version: str, risk_assessment: Dict):
        """Send rollback decision to operator on Telegram"""
        
        if not self.app:
            print(f"[OPERATOR] Cannot send Telegram message - bot not initialized")
            return
        
        message = f"""
🔴 ROLLBACK REQUIRED

Current Version: {current_version}
Target Version: {target_version}
Mutation ID: {mutation_id}

Risk Assessment:
• Data Loss Risk: {risk_assessment.get('data_loss_risk', 'UNKNOWN')}
• Fields Lost: {', '.join(risk_assessment.get('fields_lost', []))}
• Compatibility Issues: {len(risk_assessment.get('compatibility_issues', []))}

Approve rollback?
"""
        
        keyboard = [
            [
                InlineKeyboardButton("✅ APPROVE ROLLBACK", callback_data=f"rollback_approve_{mutation_id}"),
                InlineKeyboardButton("❌ REJECT ROLLBACK", callback_data=f"rollback_reject_{mutation_id}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.app.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            reply_markup=reply_markup
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle operator's button click"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        parts = callback_data.split("_", 2)
        
        if len(parts) < 3:
            await query.edit_message_text(text=f"❌ Invalid callback: {callback_data}")
            return
        
        action = parts[0]
        mutation_id = parts[2] if len(parts) > 2 else parts[1]
        
        if action == "rollback":
            action = f"{parts[0]}_{parts[1]}"
            mutation_id = parts[2]
        
        self.decision_logger.log(
            decision_type="OPERATOR_DECISION",
            metadata={
                "callback_data": callback_data,
                "action": action,
                "timestamp": datetime.now().isoformat()
            },
            mutation_id=mutation_id,
            operator_override=action.upper(),
            operator_rationale=f"Operator clicked {action} button"
        )
        
        await query.edit_message_text(
            text=f"✓ Recorded: {action.upper()} for {mutation_id}"
        )
        
        print(f"[OPERATOR] Decision recorded: {action} for {mutation_id}")
    
    async def notify_operator(self, message: str):
        """Send a notification message to operator"""
        if not self.app:
            print(f"[OPERATOR] Cannot send Telegram message - bot not initialized")
            return
        
        await self.app.bot.send_message(
            chat_id=self.chat_id,
            text=message
        )
    
    def start(self):
        """Start the Telegram bot polling"""
        if self.app:
            print(f"[OPERATOR] Starting Telegram bot...")
            self.app.run_polling()
        else:
            print("[OPERATOR] Cannot start bot - not initialized")
