# handlers/utils.py (оновлена функція)
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text="🔹 Оберіть дію нижче:"):
    # ReplyKeyboard: кнопки внизу екрану
    keyboard = [
        [KeyboardButton("➕ Додати витрату")],
        [KeyboardButton("📊 Звіти")],
        [KeyboardButton("🔙 Закрити меню")]  # Опціонально: сховати клавіатуру
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)  # resize=True для адаптації розміру
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)
        await update.callback_query.answer()  # Сховати inline-стрілку