# handlers/report_handler.py (add at end, if not there)
from telegram.ext import ContextTypes, ConversationHandler
from config import WAITING_REPORT_OWNER, WAITING_REPORT_FOP, WAITING_REPORT_TYPE  # Add if needed
from handlers.utils import send_main_menu

async def send_reports_menu(update, context: ContextTypes.DEFAULT_TYPE):
    """Показує меню звітів і повертає стан для вибору типу"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("📈 Власник", callback_data="reports_owner")],
        [InlineKeyboardButton("💼 ФОП", callback_data="reports_fop")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "📊 Оберіть тип звіту:"

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
        await update.callback_query.answer()
    return WAITING_REPORT_TYPE  # Критично: повертай стан!

async def start_report_owner(update, context: ContextTypes.DEFAULT_TYPE):
    """Перехід до введення власника"""
    query = update.callback_query
    await query.answer()
    context.user_data['report_type'] = 'owner'  # Або 'dividends'
    await query.message.edit_text("📝 Введіть ім'я власника для звіту:")
    return WAITING_REPORT_OWNER

async def start_report_fop(update, context: ContextTypes.DEFAULT_TYPE):
    """Перехід до введення ФОП"""
    query = update.callback_query
    await query.answer()
    context.user_data['report_type'] = 'fop'
    await query.message.edit_text("📝 Введіть ФОП для звіту:")
    return WAITING_REPORT_FOP

async def process_report_owner(update, context: ContextTypes.DEFAULT_TYPE):
    owner = update.message.text.strip()
    report_type = context.user_data.get('report_type', 'dividends')
    if owner:
        from reports import generate_report  # Імпорт тут, якщо потрібно
        report_text = generate_report(owner=owner, expense_type=report_type)
        await update.message.reply_text(report_text)
        context.user_data.clear()
    else:
        await update.message.reply_text("⚠️ Ім'я порожнє.")
        return WAITING_REPORT_OWNER
    await send_main_menu(update, context)
    return ConversationHandler.END

async def process_report_fop(update, context: ContextTypes.DEFAULT_TYPE):
    fop = update.message.text.strip()
    report_type = context.user_data.get('report_type', 'dividends')
    if fop:
        from reports import generate_report
        report_text = generate_report(fop=fop, expense_type=report_type)
        await update.message.reply_text(report_text)
        context.user_data.clear()
    else:
        await update.message.reply_text("⚠️ Порожнє.")
        return WAITING_REPORT_FOP
    await send_main_menu(update, context)
    return ConversationHandler.END