from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from reports import generate_report
from config import WAITING_REPORT_OWNER, WAITING_REPORT_FOP
from handlers.utils import send_main_menu

async def send_reports_menu(update):
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
    return  # Conversation продовжить у states

async def start_report_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Викликається по callback 'reports_owner'"""
    query = update.callback_query
    await query.answer()
    context.user_data['report_type'] = 'owner'  # Або dividends, залежно від логіки
    await query.message.edit_text("📝 Введіть ім'я власника для звіту:")
    return WAITING_REPORT_OWNER

async def start_report_fop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Викликається по callback 'reports_fop'"""
    query = update.callback_query
    await query.answer()
    context.user_data['report_type'] = 'fop'
    await query.message.edit_text("📝 Введіть ФОП для звіту:")
    return WAITING_REPORT_FOP

async def process_report_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner = update.message.text.strip()
    report_type = context.user_data.get('report_type', 'dividends')
    if owner:
        report_text = generate_report(owner=owner, expense_type=report_type)
        await update.message.reply_text(report_text)
        context.user_data.clear()
    else:
        await update.message.reply_text("⚠️ Ім'я порожнє.")
        return WAITING_REPORT_OWNER
    await send_main_menu(update, context)
    return ConversationHandler.END

async def process_report_fop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fop = update.message.text.strip()
    report_type = context.user_data.get('report_type', 'dividends')
    if fop:
        report_text = generate_report(fop=fop, expense_type=report_type)
        await update.message.reply_text(report_text)
        context.user_data.clear()
    else:
        await update.message.reply_text("⚠️ Порожнє.")
        return WAITING_REPORT_FOP
    await send_main_menu(update, context)
    return ConversationHandler.END