from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from handlers.main_handler import handle_callback, start, handle_message

# Спробуйте імпорт simplified_expense; якщо відсутній, заглушки
try:
    from handlers.simplified_expense import (
        WAITING_SIMPLE_DATE, WAITING_SIMPLE_MANUAL_DATE, WAITING_SIMPLE_PERIOD, WAITING_SIMPLE_SUBCATEGORY,
        WAITING_SIMPLE_AMOUNT, WAITING_SIMPLE_COMMENT, handle_simple_date, handle_simple_manual_date,
        handle_simple_period, handle_simple_subcategory, handle_simple_amount, handle_simple_comment
    )
except ImportError:
    WAITING_SIMPLE_DATE = 1001
    WAITING_SIMPLE_MANUAL_DATE = 1002
    WAITING_SIMPLE_PERIOD = 1003
    WAITING_SIMPLE_SUBCATEGORY = 1004
    WAITING_SIMPLE_AMOUNT = 1005
    WAITING_SIMPLE_COMMENT = 1006
    async def handle_simple_date(update, context): pass
    async def handle_simple_manual_date(update, context): pass
    async def handle_simple_period(update, context): pass
    async def handle_simple_subcategory(update, context): pass
    async def handle_simple_amount(update, context): pass
    async def handle_simple_comment(update, context): pass

from config import (
    WAITING_EXPENSE_TYPE, WAITING_PERIOD, WAITING_LOCATION, WAITING_CHANGE, WAITING_CATEGORY, WAITING_SUBCATEGORY,
    WAITING_SUBSUBCATEGORY, WAITING_EXPENSE_INPUT, WAITING_EXPENSE_DATE, WAITING_MANUAL_DATE,
    WAITING_REPORT_OWNER, WAITING_REPORT_FOP
)
from handlers.expense_handler import handle_expense_date_selection, handle_manual_date_input, process_expense_input
from handlers.report_handler import process_report_owner, process_report_fop

# Conversation для simplified
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_callback)],
    states={
        WAITING_SIMPLE_DATE: [CallbackQueryHandler(handle_simple_date)],
        WAITING_SIMPLE_MANUAL_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_simple_manual_date)],
        WAITING_SIMPLE_PERIOD: [CallbackQueryHandler(handle_simple_period)],
        WAITING_SIMPLE_SUBCATEGORY: [CallbackQueryHandler(handle_simple_subcategory)],
        WAITING_SIMPLE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_simple_amount)],
        WAITING_SIMPLE_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_simple_comment)],
    },
    fallbacks=[],
)

# Conversation для витрат
expense_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_callback, pattern="^add_expense$")],
    states={
        WAITING_EXPENSE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        WAITING_EXPENSE_TYPE: [CallbackQueryHandler(handle_callback, pattern="^expense_type_")],
        WAITING_PERIOD: [CallbackQueryHandler(handle_callback, pattern="^per_")],
        WAITING_LOCATION: [CallbackQueryHandler(handle_callback, pattern="^loc_")],
        WAITING_CHANGE: [CallbackQueryHandler(handle_callback, pattern="^change_")],
        WAITING_CATEGORY: [CallbackQueryHandler(handle_callback, pattern="^cat_")],
        WAITING_SUBCATEGORY: [CallbackQueryHandler(handle_callback, pattern="^sub_")],
        WAITING_SUBSUBCATEGORY: [CallbackQueryHandler(handle_callback, pattern="^subsub_")],
        WAITING_EXPENSE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_expense_input)],
        WAITING_EXPENSE_DATE: [CallbackQueryHandler(handle_expense_date_selection)],
        WAITING_MANUAL_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_date_input)],
    },
    fallbacks=[CommandHandler('start', start), MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
    per_chat=True,
    per_message=False,
)

# Conversation для звітів
report_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(handle_callback, pattern="^reports_div$"),
        CallbackQueryHandler(handle_callback, pattern="^reports_other$"),
    ],
    states={
        WAITING_REPORT_OWNER: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_report_owner)],
        WAITING_REPORT_FOP: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_report_fop)],
    },
    fallbacks=[CommandHandler('start', start), MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
    per_chat=True,
    per_message=False,
)