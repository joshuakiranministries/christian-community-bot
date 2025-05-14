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
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    keyboard = [[InlineKeyboardButton("Support Us", url=AFFILIATE_LINK)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to our Telugu Christian community! 🙏\n May the Lord bless you abundantly. \nLet’s grow together in faith.\n\n\nమన తెలుగు క్రైస్తవ సమాజానికి స్వాగతం! 🙏\n ప్రభువు మీరు అమితంగా ఆశీర్వదించాలని కోరుకుంటున్నాము. \nమనం విశ్వాసంలో కలిసి ఎదగుదాం.\nUse /verse or /prayer to start.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

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
