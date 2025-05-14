# bot.py
import os
import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, filters
from telegram.constants import ParseMode

# Bot token and admin IDs from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]
AFFILIATE_LINK = os.getenv("AFFILIATE_LINK", "https://example.com/affiliate")
WEBSITE_LINK = os.getenv("WEBSITE_LINK", "https://bibleinfotelugu.in/")

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)""")
    c.execute("""CREATE TABLE IF NOT EXISTS verses (id INTEGER PRIMARY KEY, verse TEXT, reference TEXT)""")
    conn.commit()
    conn.close()

# Sample Bible verses (replace with API or larger dataset)
VERSES = [
    {"verse": "For God so loved the world...", "reference": "John 3:16"},
    {"verse": "Trust in the Lord with all your heart...", "reference": "Proverbs 3:5"},
]

# Add user to database
def add_user(user_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# Start command
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Define the welcome message
    welcome_message = "Welcome to Christian Community Bot! 🙏\nChoose an option below:"

    # Create inline keyboard buttons
    keyboard = [
        [
            InlineKeyboardButton("Daily Verse 📖", callback_data="verse"),
            InlineKeyboardButton("Prayer 🙏", callback_data="prayer"),
        ],
        [InlineKeyboardButton("Contact Admin ✉️", callback_data="contact_admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send welcome message with buttons
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

# Verse command
async def verse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    verse = random.choice(VERSES)
    message = f"📖 <b>{verse['verse']}</b>\n— {verse['reference']}\n\nSupport our community: {AFFILIATE_LINK}"
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)

# Prayer command
async def prayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prayer_text = "Lord, guide us with your love and strength today. Amen. 🙏"
    message = f"{prayer_text}\n\nSupport us: {AFFILIATE_LINK}"
    await update.message.reply_text(message)

# Donate command
async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    donation_link = os.getenv("DONATION_LINK", "https://paypal.me/youraccount")
    await update.message.reply_text(
        f"Support our Christian Community! Donate here: {donation_link}",
        parse_mode=ParseMode.HTML
    )

# Broadcast command (admin only)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Unauthorized!")
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    message = " ".join(context.args)
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    for user in users:
        try:
            await context.bot.send_message(user[0], message, parse_mode=ParseMode.HTML)
        except Exception:
            pass
    await update.message.reply_text("Broadcast sent!")
# callback Handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query

    # Handle button clicks based on callback_data
    if query.data == "verse":
        # Call the verse function logic (same as /verse command)
        await query.message.reply_text("Here is your daily verse: [Your verse logic here]")
    elif query.data == "prayer":
        # Call the prayer function logic (same as /prayer command)
        await query.message.reply_text("Here is your prayer: [Your prayer logic here]")
    elif query.data == "contact_admin":
        # Provide admin contact or a link
        await query.message.reply_text("Contact our admin: @YourAdminUsername")

# Webhook setup
async def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("verse", verse))
    app.add_handler(CommandHandler("prayer", prayer))
    app.add_handler(CommandHandler("donate", donate))
    app.add_handler(CommandHandler("broadcast", broadcast, filters=filters.User(ADMIN_IDS)))
    # Use webhook for Render
    webhook_url = os.getenv("WEBHOOK_URL", f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook")
    await app.bot.set_webhook(webhook_url)
    return app

# Flask for webhook
from flask import Flask, request

flask_app = Flask(__name__)

@flask_app.route("/webhook", methods=["POST"])
async def webhook():
    app = await main()
    await app.initialize()  # Initialize the Application
    update = Update.de_json(request.get_json(force=True), app.bot)
    await app.process_update(update)
    return "OK", 200

@flask_app.route("/")
def home():
    return "Christian Community Bot is running!"

if __name__ == "__main__":
    init_db()
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
