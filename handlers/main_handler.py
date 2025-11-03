import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.utils import send_main_menu

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start — показ головного меню"""
    await send_main_menu(update, context, "👋 Вітаю! Обери дію нижче:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка текстових повідомлень з меню — тепер перенаправляє в conversation"""
    text = update.message.text.strip().lower()

    if "додати витрату" in text:
        # Conversation сам обробить, але якщо потрібно — можеш додати явний start
        await update.message.reply_text("🚀 Переходимо до додавання витрати...")
        return  # ConversationHandler зловить наступне
    elif "звіти" in text:
        await update.message.reply_text("📊 Переходимо до звітів...")
        return
    elif "закрити" in text or "назад" in text:
        await send_main_menu(update, context, "🔹 Меню закрито. Обери дію нижче:")
    else:
        await update.message.reply_text("⚠️ Не розпізнано. Обери дію з меню.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка callback-кнопок — тільки для загальних, решта в conversation"""
    query = update.callback_query
    data = query.data
    logging.info(f"➡️ Отримано callback: {data}")
    await query.answer()

    # Загальні кнопки (наприклад, назад — але тепер в fallbacks)
    if data == "back_main":
        await send_main_menu(update, context)
        return

    # Для add_expense та reports — тепер entry_points в conversation зловлять
    if data in ["add_expense", "reports"]:
        logging.info(f"🔄 Перенаправляємо {data} в conversation")
        return  # Не робимо нічого — handler зловить

    logging.warning(f"⚠️ Невідомий callback: {data}")
    await query.message.reply_text("⚠️ Дія не підтримується. Обери з меню.")