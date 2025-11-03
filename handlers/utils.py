from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ContextTypes

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text="🔹 Оберіть дію нижче:"):
    """Відображає головне меню користувачу."""
    keyboard = [
        [KeyboardButton("➕ Додати витрату")],
        [KeyboardButton("📊 Звіти")],
        [KeyboardButton("🔙 Закрити меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    if update.message:
        user_text = update.message.text if update.message.text else ""
        if user_text == "🔙 Закрити меню":
            await update.message.reply_text("Меню закрито 👌", reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)

    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            # 🧠 Редагуємо попереднє повідомлення, якщо можливо
            await query.message.edit_text(text)
            await query.message.reply_text(text, reply_markup=reply_markup)
        except Exception:
            # Якщо повідомлення вже не можна редагувати — просто надсилаємо нове
            await query.message.reply_text(text, reply_markup=reply_markup)

    else:
        # Фолбек на випадок нестандартного update
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=reply_markup
        )
