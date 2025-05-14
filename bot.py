import os
import telegram
import aiohttp
import random
import logging
import asyncio
import urllib.parse
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

# Assuming ADMIN_IDS and API_KEY are defined
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
API_KEY = os.getenv("GETBIBLE_API_KEY", "")

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

# Expanded fallback verses for API failure
FALLBACK_VERSES = [
    {
        "reference": "John 3:16",
        "english": "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life.",
        "telugu": "దేవుడు లోకమును ఎంతగా ప్రేమించెనంటే, తన ఏకైక కుమారునిగా జన్మించినవానిని అర్పించెను, ఆయనయందు విశ్వాసముంచు ప్రతివాడును నశించక, నిత్యజీవము పొందునట్లు."
    },
    {
        "reference": "Psalm 23:1",
        "english": "The Lord is my shepherd; I shall not want.",
        "telugu": "యెహోవా నా కాపరి, నాకు లేమి ఉండదు."
    },
    {
        "reference": "Philippians 4:13",
        "english": "I can do all things through Christ which strengtheneth me.",
        "telugu": "నన్ను బలపరిచే క్రీస్తు ద్వారా నేను సమస్తమూ చేయగలను."
    }
]

async def fetch_verse(translation: str, reference: str) -> dict:
    encoded_reference = urllib.parse.quote(reference)
    url = f"https://getbible.net/v2/{translation}/{encoded_reference}.json"
    headers = {
        "User-Agent": "ChristianCommunityBot/1.0 (https://github.com/<your-repo>)",
    }
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    if response.content_type == "application/json":
                        return await response.json()
                    else:
                        response_text = await response.text()
                        logger.error(f"Unexpected mimetype {response.content_type} from {url}. Response: {response_text[:500]}")
                        return None
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
    try:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error sending start message: {str(e)}")

async def verse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reference = random.choice(VERSE_REFERENCES)
    verse_text = ""
    try:
        english_verse = await fetch_verse("kjv", reference)
        await asyncio.sleep(1)  # Delay to avoid rate limiting
        telugu_verse = await fetch_verse("tel-irv", reference)
        if english_verse and telugu_verse:
            verse_text = (
                f"📖 *Daily Verse: {reference}*\n\n"
                f"🇬🇧 *English (KJV)*: {english_verse['text']}\n\n"
                f"🇮🇳 *Telugu (IRV)*: {telugu_verse['text']}"
            )
        else:
            fallback_verse = random.choice(FALLBACK_VERSES)
            logger.warning(f"API failed for {reference}, using fallback verse {fallback_verse['reference']}")
            verse_text = (
                f"📖 *Daily Verse: {fallback_verse['reference']}* (API unavailable, using fallback)\n\n"
                f"🇬🇧 *English (KJV)*: {fallback_verse['english']}\n\n"
                f"🇮🇳 *Telugu (IRV)*: {fallback_verse['telugu']}"
            )
    except Exception as e:
        fallback_verse = random.choice(FALLBACK_VERSES)
        logger.error(f"Error in verse function: {str(e)}")
        verse_text = (
            f"📖 *Daily Verse: {fallback_verse['reference']}* (Error occurred, using fallback)\n\n"
            f"🇬🇧 *English (KJV)*: {fallback_verse['english']}\n\n"
            f"🇮🇳 *Telugu (IRV)*: {fallback_verse['telugu']}"
        )

    try:
        if update.message:
            await update.message.reply_text(verse_text, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.message.reply_text(verse_text, parse_mode="Markdown")
        else:
            logger.error("No message or callback query found in update")
            raise ValueError("No valid message or callback query")
    except Exception as e:
        logger.error(f"Error sending verse message: {str(e)}")
        raise  # Re-raise to capture in webhook logs

async def prayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prayer_text = random.choice(PRAYERS)
    try:
        if update.message:
            await update.message.reply_text(prayer_text)
        elif update.callback_query:
            await update.callback_query.message.reply_text(prayer_text)
        else:
            logger.error("No message or callback query found in update")
    except Exception as e:
        logger.error(f"Error sending prayer message: {str(e)}")

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
    try:
        await query.answer()
        if query.data == "verse":
            await verse(update, context)
        elif query.data == "prayer":
            await prayer(update, context)
        elif query.data == "contact_admin":
            await query.message.reply_text("Contact our admin: @YourAdminUsername")
        else:
            logger.warning(f"Unknown callback data: {query.data}")
    except Exception as e:
        logger.error(f"Error in button_callback: {str(e)}")

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
    try:
        app = await main()
        update = Update.de_json(request.get_json(force=True), app.bot)
        await app.process_update(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        return "Error", 500

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
