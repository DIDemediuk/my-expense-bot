from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ContextTypes

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text="🔹 Оберіть дію нижче:"):
    """Відображає головне меню користувачу."""
    keyboard = [
        [KeyboardButton("➕ Додати витрату")],
        [KeyboardButton("📊 Звіти")],
        [KeyboardButton("🔙 Закрити меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    if update.message:
        user_text = update.message.text if update.message.text else ""
        if "закрити меню" in user_text.lower():
            await update.message.reply_text("Меню закрито 👌", reply_markup=ReplyKeyboardRemove())
            return
        await update.message.reply_text(text, reply_markup=reply_markup)

    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            logging.warning(f"Не вдалося edit: {e}. Надсилаємо нове.")
            await query.message.reply_text(text, reply_markup=reply_markup)

    else:
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)