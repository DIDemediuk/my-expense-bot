import datetime
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import WAITING_EXPENSE_DATE, WAITING_MANUAL_DATE, WAITING_EXPENSE_TYPE
from sheets import add_expense_to_sheet, parse_expense, parse_expense_simple
from handlers.utils import send_main_menu  # ← НОВИЙ: Імпорт з utils (замість main_handler)

# ... решта коду без змін (включаючи всі async функції)

async def ask_expense_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Сьогодні", callback_data="date_today")],
        [InlineKeyboardButton("📆 Вчора", callback_data="date_yesterday")],
        [InlineKeyboardButton("✏️ Ввести дату вручну", callback_data="date_manual")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # ← НОВЕ: Перевірка типу update
    if update.callback_query:
        target_message = update.callback_query.message
        await target_message.reply_text(
            "📆 Оберіть дату операції:",
            reply_markup=reply_markup
        )
        await update.callback_query.answer()  # Сховати inline-стрілку
    elif update.message:
        await update.message.reply_text(
            "📆 Оберіть дату операції:",
            reply_markup=reply_markup
        )
    else:
        logging.error("❌ Невідомий тип update в ask_expense_date")
        return ConversationHandler.END
    
    return WAITING_EXPENSE_DATE

async def handle_expense_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "date_today":
        selected_date = datetime.datetime.now().strftime("%d.%m.%Y")
    elif query.data == "date_yesterday":
        selected_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
    elif query.data == "date_manual":
        await query.message.reply_text("📝 Введіть дату у форматі ДД.ММ.РРРР (наприклад, 27.10.2025):")
        return WAITING_MANUAL_DATE
    else:
        return
    return await show_expense_type_selection(update, context, selected_date)

async def handle_manual_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.datetime.strptime(text, "%d.%m.%Y")
        selected_date = text
        return await show_expense_type_selection(update, context, selected_date)
    except ValueError:
        await update.message.reply_text("⚠️ Невірний формат. Спробуйте ще раз (ДД.ММ.РРРР):")
        return WAITING_MANUAL_DATE

async def show_expense_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, selected_date: str):
    context.user_data["selected_date"] = selected_date
    keyboard = [
        [InlineKeyboardButton("💰 Dividends", callback_data="expense_type_dividends")],
        [InlineKeyboardButton("📈 Other Expenses", callback_data="expense_type_other")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
    ]
    
    if update.callback_query:
        # ✅ ВИПРАВЛЕНО: Використовуємо edit_text, коли після вибору дати
        await update.callback_query.message.edit_text( # <-- Змінено на edit_text
            f"📅 Обрана дата: {selected_date}\n\nОбери тип:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Для ручного введення дати (update.message)
        await update.message.reply_text(
            f"📅 Обрана дата: {selected_date}\n\nОбери тип:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    return WAITING_EXPENSE_TYPE

async def process_expense_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    expense_type = context.user_data.get('expense_type', 'dividends')
    if expense_type == 'dividends':
        parsed = parse_expense(text)
    else:
        parsed = parse_expense_simple(text)
    if parsed:
        try:
            add_expense_to_sheet(parsed, context.user_data, expense_type)
            subsub = context.user_data.get('subsubcategory', '')
            await update.message.reply_text(f"✅ Додано в {expense_type}!\nСума: {parsed['сума']} грн\n{subsub}" if subsub else f"✅ Додано в {expense_type}!\nСума: {parsed['сума']} грн")
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")
    else:
        await update.message.reply_text("⚠️ Не розпізнано. Спробуй ще.")
    context.user_data.clear()
    await send_main_menu(update, context)
    return ConversationHandler.END