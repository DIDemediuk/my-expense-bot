#!/usr/bin/env python3
"""
Simplified bot.py - Main entry point for the Telegram expense bot.
This file imports conversation handlers from conversation.py module to avoid code duplication.
"""

import os
import logging
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from handlers.main_handler import start, handle_callback
from conversation import simplified_conv, expense_conv, report_conv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Reduce spam from httpx and telegram libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)

# ---------------------------
# Main Bot Initialization
# ---------------------------

if __name__ == "__main__":
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не знайдено в .env!")

    # Build application
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add conversation handlers from conversation.py
    app.add_handler(simplified_conv)
    app.add_handler(expense_conv)
    app.add_handler(report_conv)

    # Add basic command and callback handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("✅ Бот запущено!")
    app.run_polling()
