import logging
import os
import asyncio
from aiohttp import web
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from config import SHEET_MAP
from conversation import expense_conv, report_conv, conv_handler
from handlers.main_handler import start, handle_callback, handle_message

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)

async def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")

    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN не знайдено в .env або Render Environment!")
    if not WEBHOOK_URL:
        raise ValueError("❌ WEBHOOK_URL не знайдено в .env або Render Environment!")

    # Створюємо застосунок Telegram
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Додаємо всі хендлери
    application.add_handler(expense_conv)
    application.add_handler(report_conv)
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Встановлюємо webhook
    await application.bot.set_webhook(WEBHOOK_URL)

    # Створюємо aiohttp web-сервер для Render
    web_app = web.Application()
    web_app.add_routes([web.post(f"/{BOT_TOKEN}", application.webhook_update_handler())])

    port = int(os.environ.get("PORT", 10000))
    print(f"✅ Webhook запущено на порту {port}")
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    # Тримаємо сервер активним
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
