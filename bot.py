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
from telegram.error import RetryAfter, TimedOut

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
BIBLE_API_KEY = os.getenv("BIBLE_API_KEY", "")

# Validate BIBLE_API_KEY
if not BIBLE_API_KEY:
    logger.error("BIBLE_API_KEY is not set in environment variables")

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
        "telugu": "నన్ను బలపరిచే క్రీస్తు ద్వారా నేను సమస్తమవు చేయగలను."
    },
    {
        "reference": "Romans 8:28",
        "english": "And we know that all things work together for good to them that love God, to them who are the called according to his purpose.",
        "telugu": "దేవుని ప్రేమించువారికి, ఆయన సంకల్పమునుబట్టి పిలువబడినవారికి, సమస్తమును మేలుకొరకు కలిసి జరుగునని మనము ఎరుగుదుము."
    },
    {
        "reference": "Jeremiah 29:11",
        "english": "For I know the thoughts that I think toward you, saith the Lord, thoughts of peace, and not of evil, to give you an expected end.",
        "telugu": "మీ గురించి నేను తలంచిన ఆలోచనలు నాకు తెలిసినవని యెహోవా వాక్కు; అవి మీకు శాంతి కలుగునట్లు కీడుకు కాక ఒక అంతము కలుగునట్లు ఆలోచనలు."
    }
]

# Convert verse reference to api.bible format (e.g., "John 3:16" -> "JHN.3.16")
def format_verse_reference(reference: str) -> str:
    try:
        book, chapter_verse = reference.rsplit(" ", 1)
        chapter, verse = chapter_verse.split(":")
        book_abbr = {
            "John": "JHN",
            "Psalm": "PSA",
            "Romans": "ROM",
            "Philippians": "PHP",
            "Jeremiah": "JER",
            "Proverbs": "PRO",
            "Matthew": "MAT",
            "Isaiah": "ISA",
            "1 Corinthians": "1CO",
            "Ephesians": "EPH"
        }.get(book, book.upper()[:3])
        return f"{book_abbr}.{chapter}.{verse}"
    except Exception as e:
        logger.error(f"Error formatting verse reference {reference}: {str(e)}")
        return reference.replace(" ", ".").replace(":", ".")

async def fetch_verse(translation: str, reference: str) -> dict:
    bible_id = {
        "kjv": "de4e12af7f28f599-01",  # KJV
        "tel-irv": "a156e704dc937475-01"  # Telugu IRV
    }.get(translation)
    if not bible_id:
        logger.error(f"Invalid translation: {translation}")
        return None
    verse_id = format_verse_reference(reference)
    url = f"https://api.bible/v1/bibles/{bible_id}/verses/{verse_id}"
    headers = {
        "api-key": BIBLE_API_KEY,
        "User-Agent": "ChristianCommunityBot/1.0 (https://github.com/<your-repo>)",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                logger.info(f"API request to {url}: Status {response.status}, Headers {response.headers}")
                if response.status == 200:
                    if response.content_type == "application/json":
                        data = await response.json()
                        return {"text": data["data"]["content"]}
                    else:
                        response_text = await response.text()
                        logger.error(f"Unexpected mimetype {response.content_type} from {url}. Response: {response_text[:500]}")
                        return None
                else:
                    response_text = await response.text()
                    logger.error(f"Failed to fetch verse from {url}: Status {response.status}, Response: {response_text[:500]}")
                    return None
    except aiohttp.ClientError as e:
        logger.error(f"Client error fetching verse from {url}: {str(e)}")
        return None
    except asyncio.TimeoutError:
        logger.error(f"Timeout fetching verse from {url}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching verse from {url}: {str(e)}")
        return None

async def send_message_with_retry(update: Update, text: str, parse_mode: str = None, reply_markup=None, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            if update.message:
                await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
            elif update.callback_query:
                await update.callback_query.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
            else:
                logger.error("No message or callback query found in update")
                raise ValueError("No valid message or callback query")
            logger.info(f"Message sent successfully: {text[:50]}...")
            return
        except RetryAfter as e:
            logger.warning(f"RetryAfter error: {e}. Waiting {e.retry_after} seconds...")
            await asyncio.sleep(e.retry_after + 1)  # Add buffer
        except TimedOut:
            logger.warning(f"TimedOut error on attempt {attempt + 1}. Retrying...")
            await asyncio.sleep(2 ** attempt + 1)
        except Exception as e:
            logger.error(f"Error sending message (attempt {attempt + 1}): {str(e)}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt + 1)

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
        await send_message_with_retry(update, welcome_message, parse_mode="Markdown", reply_markup=reply_markup)
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
        await send_message_with_retry(update, verse_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error sending verse message: {str(e)}")
        raise

async def prayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prayer_text = random.choice(PRAYERS)
    try:
        await send_message_with_retry(update, prayer_text)
    except Exception as e:
        logger.error(f"Error sending prayer message: {str(e)}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        logger.error("No message found in update for broadcast command")
        return
    try:
        message = update.message.text.split(" ", 1)[1]
    except IndexError:
        await send_message_with_retry(update, "Please provide a message to broadcast. Usage: /broadcast <message>")
        return
    for user_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except telegram.error.TelegramError as e:
            logger.error(f"Failed to send broadcast to {user_id}: {e}")
    await send_message_with_retry(update, "Broadcast sent!")

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
            await send_message_with_retry(update, "Contact our admin: @YourAdminUsername")
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
