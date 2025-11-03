import os
import logging
import asyncio
from aiohttp import web
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from config import SHEET_MAP
from conversation import expense_conv, report_conv, conv_handler
from handlers.main_handler import start, handle_callback, handle_message

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get("PORT", "10000"))  # Render відкриває цей порт автоматично
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не знайдено в .env!")

    app = Application.builder().token(BOT_TOKEN).build()

    # Додаємо всі хендлери
    app.add_handler(expense_conv)
    app.add_handler(report_conv)
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    async def handle(request):
        data = await request.json()
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
        return web.Response()

    # Webhook сервер через aiohttp
    runner = web.AppRunner(web.Application())
    site_app = runner.app
    site_app.router.add_post(f"/{BOT_TOKEN}", handle)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    # Реєструємо webhook у Telegram
    await app.bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")
    logger.info(f"✅ Webhook встановлено: {WEBHOOK_URL}/{BOT_TOKEN}")

    # Не завершуємо процес
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())

