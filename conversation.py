from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from handlers.main_handler import handle_callback, start, handle_message
from handlers.expense_handler import (
    handle_expense_date_selection, handle_manual_date_input,
    process_expense_input, handle_back_to_main
)
from handlers.report_handler import process_report_owner, process_report_fop
from config import (
    WAITING_EXPENSE_TYPE, WAITING_PERIOD, WAITING_LOCATION, WAITING_CHANGE,
    WAITING_CATEGORY, WAITING_SUBCATEGORY, WAITING_SUBSUBCATEGORY, WAITING_EXPENSE_INPUT,
    WAITING_EXPENSE_DATE, WAITING_MANUAL_DATE, WAITING_REPORT_OWNER, WAITING_REPORT_FOP
)

# --- simplified (залишаємо як є, щоб не ламати інші блоки)
try:
    from handlers.simplified_expense import (
        WAITING_SIMPLE_DATE, WAITING_SIMPLE_MANUAL_DATE, WAITING_SIMPLE_PERIOD,
        WAITING_SIMPLE_SUBCATEGORY, WAITING_SIMPLE_AMOUNT, WAITING_SIMPLE_COMMENT,
        handle_simple_date, handle_simple_manual_date, handle_simple_period,
        handle_simple_subcategory, handle_simple_amount, handle_simple_comment
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

# --- Основний flow для витрат
expense_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_callback, pattern="^add_expense$")],
    states={
        WAITING_EXPENSE_DATE: [
            CallbackQueryHandler(handle_expense_date_selection),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],
        WAITING_MANUAL_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_date_input),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],
        WAITING_EXPENSE_TYPE: [
            CallbackQueryHandler(handle_callback, pattern="^expense_type_"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],
        WAITING_EXPENSE_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_expense_input),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],
    },
    fallbacks=[CommandHandler('start', start)],
    per_chat=True,
    per_message=False,
)

# --- Звіти
report_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(handle_callback, pattern="^reports_div$"),
        CallbackQueryHandler(handle_callback, pattern="^reports_other$"),
    ],
    states={
        WAITING_REPORT_OWNER: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_report_owner)],
        WAITING_REPORT_FOP: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_report_fop)],
    },
    fallbacks=[CommandHandler('start', start)],
    per_chat=True,
    per_message=False,
)
