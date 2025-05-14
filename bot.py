import os
import telegram
import aiohttp
import random
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Assuming ADMIN_IDS is defined
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

# List of verse references for random selection
VERSE_REFERENCES = [
    "John 3:16", "Psalm 23:1", "Romans 8:28", "Philippians 4:13", "Jeremiah 29:11",
    "Proverbs 3:5", "Matthew 5:16", "Isaiah 40:31", "1 Corinthians 13:4", "Ephesians 2:8"
]

# List of sample prayers for random selection
PRAYERS = [
    "May God bless you with peace and strength today. Amen.",
    "Lord, guide us with your wisdom and love. Amen.",
    "Heavenly Father, protect us and grant us your grace. Amen."
]

async def fetch_verse(translation: str, reference: str) -> dict:
    url = f"https://getbible.net/v2/{translation}/{reference}.json"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to fetch verse from {url}: Status {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error fetching verse from {url}: {str(e)}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = "Welcome to Christian Community Bot! 🙏\nChoose an option below:"
    keyboard = [
        [
            InlineKeyboardButton("Daily Verse 📖", callback_data="verse"),
            InlineKeyboardButton("Prayer 🙏", callback_data="prayer"),
        ],
        [InlineKeyboardButton("Contact Admin ✉️", callback_data="contact_admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def verse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reference = random.choice(VERSE_REFERENCES)
    try:
        english_verse = await fetch_verse("kjv", reference)
        telugu_verse = await fetch_verse("tel-irv", reference)
        if english_verse and telugu_verse:
            verse_text = (
                f"📖 *Daily Verse: {reference}*\n\n"
                f"🇬🇧 *English (KJV)*: {english_verse['text']}\n\n"
                f"🇮🇳 *Telugu (IRV)*: {telugu_verse['text']}"
            )
        else:
            verse_text = f"Sorry, could not fetch the verse for {reference}. Please try again later."
    except Exception as e:
        verse_text = f"Error fetching verse: {str(e)}. Please try again later."
        logger.error(f"Error in verse function: {str(e)}")
    
    if update.message:
        await update.message.reply_text(verse_text, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.reply_text(verse_text, parse_mode="Markdown")

async def prayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prayer_text = random.choice(PRAYERS)
    if update.message:
        await update.message.reply_text(prayer_text)
    elif update.callback_query:
        await update.callback_query.message.reply_text(prayer_text)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        logger.error("No message found in update for broadcast command")
        return
    try:
        message = update.message.text.split(" ", 1)[1]
    except IndexError:
        await update.message.reply_text("Please provide a message to broadcast. Usage: /broadcast <message>")
        return
    for user_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except telegram.error.TelegramError as e:
            logger.error(f"Failed to send broadcast to {user_id}: {e}")
    await update.message.reply_text("Broadcast sent!")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    logger.info(f"Received callback query with data: {query.data}")
    await query.answer()
    if query.data == "verse":
        await verse(update, context)
    elif query.data == "prayer":
        await prayer(update, context)
    elif query.data == "contact_admin":
        await query.message.reply_text("Contact our admin: @YourAdminUsername")
    else:
        logger.warning(f"Unknown callback data: {query.data}")

async def main():
    app = Application.builder().token(os.getenv("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("verse", verse))
    app.add_handler(CommandHandler("prayer", prayer))
    app.add_handler(CommandHandler("broadcast", broadcast, filters=filters.User(ADMIN_IDS)))
    app.add_handler(CallbackQueryHandler(button_callback))
    await app.initialize()
    return app

from flask import Flask, request
flask_app = Flask(__name__)

@flask_app.route("/webhook", methods=["POST"])
async def webhook():
    app = await main()
    update = Update.de_json(request.get_json(force=True), app.bot)
    await app.process_update(update)
    return "OK", 200

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
