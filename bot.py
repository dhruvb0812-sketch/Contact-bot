import os
import logging
import asyncio
from datetime import datetime, timedelta
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from threading import Thread
import re

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
YOUR_USER_ID = int(os.environ.get("YOUR_USER_ID", 123456789))  # Your Telegram ID
PORT = int(os.environ.get("PORT", 8080))

# Flask app for uptime monitoring
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 Bot is running!", 200

@flask_app.route('/health')
def health():
    return {"status": "alive", "timestamp": datetime.now().isoformat()}, 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=PORT)

# Store forwarded messages temporarily
forwarded_messages = {}

# Helper functions
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📝 About Me", callback_data="about")],
        [InlineKeyboardButton("💼 Services", callback_data="services")],
        [InlineKeyboardButton("⭐ Reviews", callback_data="reviews")],
        [InlineKeyboardButton("⚠️ Report Issue", callback_data="report")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    user = update.effective_user
    welcome_text = f"""
✨ *Welcome {user.first_name}!* ✨

I'm a contact bot for *{context.bot.username}*. 
Use the buttons below to get information or contact the owner.

💡 *Tip:* You can send any message here, and the owner will reply when available!

*Available Commands:*
/start - Restart the bot
/help - Show help
/about - About the owner
/contact - Contact the owner
"""
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message."""
    help_text = """
🤖 *Bot Commands & Features*

• Send any message - I'll forward it to the owner
• Use buttons to learn more about services
• Owner will reply to you through the bot

*Response Time:* Usually within 24 hours
*Privacy:* Your identity remains hidden

*Need immediate help?* 
Send "URGENT" in your message for priority response!

For any issues, use the Report Issue button.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send about information."""
    about_text = """
👨‍💻 *About the Owner*

• Professional with 5+ years experience
• Specialized in multiple domains
• Committed to quality service

*Qualifications:*
✅ Certified Professional
✅ 1000+ satisfied clients
✅ 24/7 availability

Use the contact feature to reach out!
"""
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle contact command."""
    await update.message.reply_text(
        "📨 *How to Contact Owner*\n\n"
        "Just send me any message and I'll forward it directly!\n\n"
        "*Tips for faster response:*\n"
        "• Be clear about your query\n"
        "• Add relevant details\n"
        "• Mention 'URGENT' if needed\n\n"
        "Start typing your message below 👇",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward user message to owner."""
    user = update.effective_user
    message = update.effective_message
    
    # Check if it's the owner replying
    if user.id == YOUR_USER_ID and message.reply_to_message:
        # Owner is replying to a user
        original_msg_id = message.reply_to_message.message_id
        if original_msg_id in forwarded_messages:
            target_user_id = forwarded_messages[original_msg_id]
            reply_text = f"📨 *Reply from Owner:*\n\n{message.text}"
            
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=reply_text,
                    parse_mode='Markdown'
                )
                await message.reply_text("✅ Reply sent successfully!")
                # Clean up old entry
                del forwarded_messages[original_msg_id]
            except Exception as e:
                logger.error(f"Error sending reply: {e}")
                await message.reply_text("❌ Failed to send reply. User might have blocked the bot.")
        else:
            await message.reply_text("⚠️ Couldn't find original message context.")
        return
    
    # Regular user message (not owner)
    if user.id != YOUR_USER_ID:
        # Detect urgency
        is_urgent = "urgent" in message.text.lower() if message.text else False
        
        # Prepare forward message
        user_info = f"""
👤 *New Message from User*

┌ *Name:* {user.first_name} {user.last_name or ''}
├ *ID:* `{user.id}`
├ *Username:* @{user.username if user.username else 'N/A'}
├ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'├ *URGENCY:* ⚠️ URGENT ⚠️' if is_urgent else ''}
└ *Message:* 

{message.text if message.text else '📎 Media message'}
"""
        
        # Forward message to owner
        forwarded_msg = None
        if message.text:
            forwarded_msg = await context.bot.send_message(
                chat_id=YOUR_USER_ID,
                text=user_info,
                parse_mode='Markdown'
            )
        elif message.photo:
            # Forward photo with caption
            forwarded_msg = await context.bot.send_photo(
                chat_id=YOUR_USER_ID,
                photo=message.photo[-1].file_id,
                caption=user_info,
                parse_mode='Markdown'
            )
        else:
            # Handle other media types (video, document, audio)
            forwarded_msg = await context.bot.send_message(
                chat_id=YOUR_USER_ID,
                text=user_info,
                parse_mode='Markdown'
            )
        
        # Store mapping for replies
        if forwarded_msg:
            forwarded_messages[forwarded_msg.message_id] = user.id
            
            # Clean up old mappings (older than 1 hour)
            current_time = datetime.now()
            for msg_id in list(forwarded_messages.keys()):
                if msg_id < current_time - timedelta(hours=1):
                    del forwarded_messages[msg_id]
        
        # Send confirmation to user
        confirm_text = "📨 *Message sent!*\n\n" + (
            "⚠️ *URGENT flag detected!* Owner will respond ASAP!\n\n" if is_urgent else ""
        ) + "Owner will reply to you here shortly. Please wait patiently.\n\n"
        
        await update.message.reply_text(
            confirm_text + "Use /help for more options.",
            parse_mode='Markdown'
        )
        
        # Log the interaction
        logger.info(f"Message forwarded from user {user.id}")
    else:
        # Owner sending without reply context
        await update.message.reply_text(
            "ℹ️ To reply to a user, use the *reply feature* on their forwarded message.",
            parse_mode='Markdown'
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "main_menu":
        await query.edit_message_text(
            "✨ *Main Menu*\nChoose an option below:",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
    elif query.data == "about":
        text = """
👨‍💻 *About Me*

I'm a dedicated professional with extensive experience in:
• Web Development
• Digital Marketing  
• Content Creation
• Consulting Services

*Mission:* Delivering excellence in every project

*Contact me for:* Custom solutions tailored to your needs
"""
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=get_back_keyboard())
    
    elif query.data == "services":
        text = """
💼 *Services Offered*

*Main Services:*
• 🤖 Bot Development
• 🌐 Web Design
• 📱 App Development
• 📈 SEO Optimization
• 🎨 Graphic Design

*Packages starting from $50*

Send "SERVICES" in your message for detailed pricing!
"""
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=get_back_keyboard())
    
    elif query.data == "reviews":
        text = """
⭐ *Client Reviews*

"Excellent work! Very professional." - ★★★★★
"Fast delivery, great communication." - ★★★★★
"Would definitely recommend!" - ★★★★★
"Above and beyond expectations." - ★★★★★

*Total Reviews:* 150+ ★★★★★ (5.0 average)

*Recent Projects:* Completed 50+ projects in last month
"""
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=get_back_keyboard())
    
    elif query.data == "report":
        text = """
⚠️ *Report an Issue*

Having trouble? Please describe your issue in a message and I'll address it ASAP.

*Common issues:*
• Bot not responding
• Late replies
• Technical problems
• Service concerns

*Escalation:* For urgent issues, mention "ESCALATE" in your message
"""
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=get_back_keyboard())
    
    elif query.data == "help":
        text = """
❓ *Help Center*

*Quick Guide:*
1️⃣ Send any message to contact me
2️⃣ I'll reply through this bot
3️⃣ Use buttons for information

*FAQs:*
Q: How fast do you reply?
A: Usually within 24 hours

Q: Is my data safe?  
A: Yes, messages are private

Q: Do you offer refunds?
A: Depends on the service

*Support Hours:* 24/7 Emergency support available
"""
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=get_back_keyboard())

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot."""
    # Create Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("contact", contact_command))
    
    # Add message handler (for all messages)
    application.add_handler(MessageHandler(filters.ALL, handle_message))
    
    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start Flask in separate thread for uptime
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Start the Bot
    print("🤖 Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
