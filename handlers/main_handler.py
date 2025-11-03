import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.utils import send_main_menu
from handlers.expense_handler import ask_expense_date

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start — показ головного меню"""
    await send_main_menu(update, context, "👋 Вітаю! Обери дію нижче:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка текстових повідомлень з меню"""
    text = update.message.text.strip().lower()

    if "додати витрату" in text:
        await ask_expense_date(update, context)
    elif "звіти" in text:
        await send_reports_menu(update)
    elif "закрити" in text or "назад" in text:
        await send_main_menu(update, context, "🔹 Меню закрито. Обери дію нижче:")
    else:
        await update.message.reply_text("⚠️ Не розпізнано. Обери дію з меню.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка callback-кнопок (inline-кнопки, не знизу меню)"""
    query = update.callback_query
    data = query.data
    logging.info(f"➡️ Отримано callback: {data}")
    await query.answer()

    # Кнопка «Назад» з будь-якого меню
    if data == "back_main":
        await send_main_menu(update, context)
        return

    # Якщо користувач натиснув «Додати витрату» (через inline)
    if data == "add_expense":
        await ask_expense_date(update, context)
        return

    # Якщо «Звіти»
    if data == "reports":
        await send_reports_menu(update)
        return

    # Інше — просто логування (для майбутніх дій)
    logging.warning(f"⚠️ Невідомий callback: {data}")
    await query.message.reply_text("⚠️ Дія не підтримується. Обери з меню.")
    

# 👇 допоміжне меню “Звіти”
async def send_reports_menu(update: Update):
    keyboard = [
        [InlineKeyboardButton("📈 Власник", callback_data="reports_owner")],
        [InlineKeyboardButton("💼 ФОП", callback_data="reports_fop")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("📊 Оберіть тип звіту:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text("📊 Оберіть тип звіту:", reply_markup=reply_markup)
        await update.callback_query.answer()
