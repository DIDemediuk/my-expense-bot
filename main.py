import os
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from conversation import expense_conv, report_conv, conv_handler
from handlers.main_handler import start, handle_callback, handle_message
import asyncio

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # ✅ Використовуємо з .env

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(expense_conv)
    app.add_handler(report_conv)
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    full_webhook_url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
    await app.bot.set_webhook(full_webhook_url)
    logging.info(f"✅ Webhook встановлено: {full_webhook_url}")

    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", "8080")),
        webhook_url=full_webhook_url
    )

if __name__ == "__main__":
    asyncio.run(main())
