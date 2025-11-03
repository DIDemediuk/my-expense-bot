import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ConversationHandler
)
from aiohttp import web

from config import SHEET_MAP
from conversation import expense_conv, report_conv, conv_handler
from handlers.main_handler import start, handle_callback, handle_message

load_dotenv()

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://my-expense-bot.onrender.com

app = ApplicationBuilder().token(BOT_TOKEN).build()

# --- Handlers ---
app.add_handler(expense_conv)
app.add_handler(report_conv)
app.add_handler(conv_handler)
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# --- Webhook Handler ---
async def handle(request):
    """Обробка POST запитів від Telegram."""
    update = Update.de_json(await request.json(), app.bot)
    await app.process_update(update)
    return web.Response(text="OK")

async def main():
    await app.initialize()  # 🔹 важливо!
    await app.bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")

    server = web.Application()
    server.router.add_post(f"/{BOT_TOKEN}", handle)

    runner = web.AppRunner(server)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"✅ Webhook встановлено: {WEBHOOK_URL}/{BOT_TOKEN}")

    # Залишити сервер запущеним
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
