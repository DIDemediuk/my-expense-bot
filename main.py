import logging
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import SHEET_MAP  # Для перевірки
from conversation import expense_conv, report_conv, conv_handler
from handlers.main_handler import start, handle_callback, handle_message

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)

if __name__ == "__main__":
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не знайдено в .env!")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(expense_conv)
    app.add_handler(report_conv)
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # Замість старого, тепер обробляє кнопки
    print("✅ Бот запущено!")
    app.run_polling()