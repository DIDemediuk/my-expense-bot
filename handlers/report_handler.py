from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from reports import generate_report
from config import WAITING_REPORT_OWNER, WAITING_REPORT_FOP
from handlers.utils import send_main_menu  # ← НОВИЙ: Імпорт з utils

# ... решта коду без змін

async def process_report_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner = update.message.text.strip()
    report_type = context.user_data.get('report_type', 'dividends')
    if owner:
        report_text = generate_report(owner=owner, expense_type=report_type)
        await update.message.reply_text(report_text)
        context.user_data.pop('report_type', None)
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
        context.user_data.pop('report_type', None)
    else:
        await update.message.reply_text("⚠️ Порожнє.")
        return WAITING_REPORT_FOP
    await send_main_menu(update, context)
    return ConversationHandler.END