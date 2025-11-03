# main.py (ФІНАЛЬНА ВЕРСІЯ)
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
    filters,
)

# ✅ 1. ІМПОРТУЄМО ВСІ ХЕНДЛЕРИ ТА CONVERSATION HANDLER'И
from config import SHEET_MAP
from conversation import expense_conv, report_conv, conv_handler
from handlers.main_handler import start, handle_callback, handle_message # start, handle_callback, handle_message

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Глобальні змінні для Webhook ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get("PORT", "10000")) 
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не знайдено в .env або змінних середовища!")

# ✅ 2. Створення об'єкта Application (на рівні модуля, щоб був доступний handle)
app = Application.builder().token(BOT_TOKEN).build()

app_init_loop = asyncio.get_event_loop()
app_init_loop.run_until_complete(app.initialize())

# ✅ 3. Обробник вхідного Webhook-запиту
async def handle(request):
    """Обробляє вхідні POST-запити від Telegram."""
    data = await request.json()
    # Конвертуємо JSON-оновлення у об'єкт Update
    update = Update.de_json(data, app.bot)
    
    # Обробляємо оновлення. app.initialize() має бути вже викликано в main()
    await app.process_update(update) 
    return web.Response()


# ✅ 4. Основна функція запуску
async def main():
    # 4.1. Додаємо всі хендлери до Application
    # Ці об'єкти тепер доступні, бо імпортовані на рівні модуля (рядок 17)
    app.add_handler(expense_conv)
    app.add_handler(report_conv)
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

 

    # 4.3. Встановлення Webhook
    if WEBHOOK_URL:
        full_webhook_url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
        await app.bot.set_webhook(url=full_webhook_url)
        logging.info(f"✅ Webhook встановлено: {full_webhook_url}")
    else:
        logging.warning("⚠️ WEBHOOK_URL не встановлено. Бот працюватиме у режимі Long Polling (локально) або не запуститься на Render.")


    # 4.4. Запуск aiohttp Webhook сервера
    runner = web.AppRunner(web.Application())
    site_app = runner.app
    # Прив'язуємо обробник `handle` до шляху з токеном
    site_app.router.add_post(f"/{BOT_TOKEN}", handle)
    await runner.setup()
    
    # Запускаємо сервер на 0.0.0.0:[PORT]
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"🚀 Сервер aiohttp запущено на порту {PORT}")

    # 4.5. Утримуємо цикл живим
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        logging.info("🤖 Запуск бота...")
        asyncio.run(main())
    except Exception as e:
        logging.error(f"❌ Фатальна помилка при запуску: {e}")