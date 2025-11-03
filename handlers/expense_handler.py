import datetime
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import WAITING_EXPENSE_DATE, WAITING_MANUAL_DATE, WAITING_EXPENSE_TYPE
from sheets import add_expense_to_sheet, parse_expense, parse_expense_simple
from handlers.utils import send_main_menu

async def ask_expense_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Сьогодні", callback_data="date_today")],
        [InlineKeyboardButton("📆 Вчора", callback_data="date_yesterday")],
        [InlineKeyboardButton("✏️ Ввести дату вручну", callback_data="date_manual")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.reply_text("📆 Оберіть дату операції:", reply_markup=reply_markup)
        await update.callback_query.answer()
    elif update.message:
        await update.message.reply_text("📆 Оберіть дату операції:", reply_markup=reply_markup)
    else:
        logging.error("❌ Невідомий тип update в ask_expense_date")
        return ConversationHandler.END

    return WAITING_EXPENSE_DATE

async def handle_expense_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "date_today":
        selected_date = datetime.datetime.now().strftime("%d.%m.%Y")
        return await show_expense_type_selection(update, context, selected_date)
    elif query.data == "date_yesterday":
        selected_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
        return await show_expense_type_selection(update, context, selected_date)
    elif query.data == "date_manual":
        await query.message.reply_text("📝 Введіть дату у форматі ДД.ММ.РРРР (наприклад, 27.10.2025):")
        return WAITING_MANUAL_DATE
    elif query.data == "back_main":
        return await handle_back_to_main(update, context)
    return WAITING_EXPENSE_DATE  # Фолбек

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
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"📅 Обрана дата: {selected_date}\n\nОбери тип:"
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)
    return WAITING_EXPENSE_TYPE

# Додай це: обробка вибору типу (callback перед введенням суми)
async def handle_expense_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    expense_type = 'dividends' if query.data == "expense_type_dividends" else 'other'
    context.user_data['expense_type'] = expense_type
    await query.message.edit_text(
        f"✅ Тип: {expense_type.upper()}\n\nВведи деталі витрати (сума + опис, напр. '500 Бензин'):"
    )
    return WAITING_EXPENSE_TYPE  # Тепер чекаємо текст

# Онови process_expense_input — використовуй handle_expense_type_selection в states
async def process_expense_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    expense_type = context.user_data.get('expense_type', 'dividends')
    selected_date = context.user_data.get('selected_date', datetime.datetime.now().strftime("%d.%m.%Y"))

    if expense_type == 'dividends':
        parsed = parse_expense(text)
    else:
        parsed = parse_expense_simple(text)

    if parsed:
        try:
            parsed['дата'] = selected_date  # Додай дату, якщо не було
            add_expense_to_sheet(parsed, context.user_data, expense_type)
            subsub = context.user_data.get('subsubcategory', '')
            msg = f"✅ Додано в {expense_type}!\nСума: {parsed['сума']} грн"
            if subsub:
                msg += f"\n{subsub}"
            await update.message.reply_text(msg)
        except Exception as e:
            await update.message.reply_text(f"❌ Помилка: {e}")
            logging.error(f"❌ Expense error: {e}")
    else:
        await update.message.reply_text("⚠️ Не розпізнано. Спробуй ще (сума + опис).")

    context.user_data.clear()
    await send_main_menu(update, context)
    return ConversationHandler.END

async def handle_back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    context.user_data.clear()
    await send_main_menu(update, context)
    return ConversationHandler.END