import logging
import telegram

# Telegram bot token
TOKEN = 'YOUR_BOT_TOKEN'

def send_status(update, context):
    # Send the status update to the Telegram channel
    context.bot.send_message(chat_id=update.effective_chat.id, text='Agent status: online')

def main():
    # Initialize the Telegram bot
    updater = telegram.ext.Updater(TOKEN, use_context=True)
    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    # Register the status reporter
    dp.add_handler(CommandHandler('status', send_status))
    # Start the bot
    updater.start_polling()
    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()