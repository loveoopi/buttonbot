import os
import logging
import re
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Dictionary to store filters {trigger_word: {'text': response, 'buttons': []}}
filters_dict = {}
# Track which users are currently setting up buttons
button_setup_mode = {}

# Command handlers
def start(update, context):
    update.message.reply_text('Hi! I am your filter bot. Use /filterr to add new filters.')

def add_filter(update, context):
    """Add a new filter when user replies to a message with /filterr trigger"""
    reply = update.message.reply_to_message
    if not reply:
        update.message.reply_text('You need to reply to a message to set a filter!')
        return
    
    try:
        trigger = context.args[0].lower()
    except IndexError:
        update.message.reply_text('Please provide a trigger word!\nUsage: /filterr trigger_word')
        return
    
    # Store just the text for now (buttons will be added separately)
    response = reply.text
    filters_dict[trigger] = {'text': response, 'buttons': []}
    
    # Set user in button setup mode
    user_id = update.message.from_user.id
    button_setup_mode[user_id] = trigger
    
    # Ask for button information
    update.message.reply_text(
        f'✅ Filter "{trigger}" added successfully!\n\n'
        'Now send button information in this format:\n'
        'Button Name - URL\n'
        'For example:\n'
        'Google - https://google.com\n'
        'YouTube - https://youtube.com\n\n'
        'Send "done" when finished adding buttons.'
    )

def handle_message(update, context):
    """Check messages for triggers and respond accordingly"""
    user_id = update.message.from_user.id
    
    # Check if user is in button setup mode
    if user_id in button_setup_mode:
        handle_button_info(update, context)
        return
    
    message_text = update.message.text.lower()
    
    # Check if any trigger word exists in the message
    for trigger, filter_data in filters_dict.items():
        if re.search(r'\b' + re.escape(trigger) + r'\b', message_text):
            # Create inline keyboard if buttons exist
            if filter_data['buttons']:
                keyboard = []
                for button in filter_data['buttons']:
                    keyboard.append([InlineKeyboardButton(button['text'], url=button['url'])])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text(filter_data['text'], reply_markup=reply_markup)
            else:
                update.message.reply_text(filter_data['text'])
            break  # Only respond to the first match

def handle_button_info(update, context):
    """Handle button information input"""
    user_id = update.message.from_user.id
    message_text = update.message.text.strip()
    
    if user_id not in button_setup_mode:
        return
    
    trigger = button_setup_mode[user_id]
    
    if message_text.lower() == 'done':
        del button_setup_mode[user_id]
        update.message.reply_text('Button setup completed!')
        return
    
    # Parse button information (format: "Button Name - URL")
    if ' - ' not in message_text:
        update.message.reply_text('Invalid format. Please use: Button Name - URL')
        return
    
    button_name, button_url = message_text.split(' - ', 1)
    button_name = button_name.strip()
    button_url = button_url.strip()
    
    # Add button to the filter
    if trigger in filters_dict:
        filters_dict[trigger]['buttons'].append({'text': button_name, 'url': button_url})
        update.message.reply_text(f'✅ Button "{button_name}" added! Send more buttons or "done" to finish.')
    else:
        update.message.reply_text('Error: Filter not found. Please start over with /filterr')
        del button_setup_mode[user_id]

def stop_all(update, context):
    """Remove all filters"""
    global filters_dict
    if not filters_dict:
        update.message.reply_text('No filters to remove!')
        return
    
    count = len(filters_dict)
    filters_dict = {}
    update.message.reply_text(f'🗑️ Removed all {count} filters!')

def list_filters(update, context):
    """List all active filters"""
    if not filters_dict:
        update.message.reply_text('No active filters!')
        return
    
    filters_list = []
    for trigger, data in filters_dict.items():
        button_count = len(data['buttons'])
        filters_list.append(f"• {trigger} ({button_count} buttons)")
    
    update.message.reply_text(f"Active filters:\n" + "\n".join(filters_list))

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Telegram Bot is running!')
    
    def log_message(self, format, *args):
        # Disable logging for HTTP requests
        return

def run_http_server():
    """Run a simple HTTP server to satisfy Heroku's requirements"""
    port = int(os.environ.get('PORT', 5000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    print(f"HTTP server running on port {port}")
    server.serve_forever()

def run_bot():
    """Run the Telegram bot"""
    # Your bot token (hardcoded as requested)
    token = "8331125251:AAGbLMI3syQyGtdy7g22WuFNO2tsIFjjf1E"
    
    # Create Updater
    updater = Updater(token, use_context=True)

    # Get dispatcher to register handlers
    dp = updater.dispatcher

    # Add command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("filterr", add_filter))
    dp.add_handler(CommandHandler("stopalll", stop_all))
    dp.add_handler(CommandHandler("list", list_filters))

    # Add message handler for all text messages
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Log all errors
    dp.add_error_handler(error)

    # Start the Bot
    print("Bot started...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    # Start the HTTP server in a separate thread
    http_thread = threading.Thread(target=run_http_server)
    http_thread.daemon = True
    http_thread.start()
    
    # Run the bot in the main thread
    run_bot()
