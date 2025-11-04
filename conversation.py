from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from handlers.main_handler import start, handle_message, handle_callback  # Додали handle_callback назад до імпорту
from handlers.expense_handler import (
    ask_expense_date, handle_expense_date_selection, handle_manual_date_input,
    handle_expense_type_selection, process_expense_input, handle_back_to_main  # Додали ask_expense_date та handle_expense_type_selection (з попереднього фіксу)
)
from handlers.expense_handler import (
    ask_expense_date, handle_expense_date_selection, handle_manual_date_input,
    handle_expense_type_selection, process_expense_input,
    # ✅ ДОДАЄМО НОВІ ФУНКЦІЇ
    handle_period_selection, handle_location_selection,
    # ... інші handle_selection
)
from config import (
    WAITING_EXPENSE_TYPE, WAITING_PERIOD, WAITING_LOCATION, WAITING_CHANGE,
    WAITING_CATEGORY, WAITING_SUBCATEGORY, WAITING_SUBSUBCATEGORY, WAITING_EXPENSE_INPUT,
    WAITING_EXPENSE_DATE, WAITING_MANUAL_DATE, WAITING_REPORT_OWNER, WAITING_REPORT_FOP
)

# --- simplified (залишаємо як є, але додамо fallbacks для back_main, якщо потрібно)
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

# Додай fallback для simplified (якщо є back_main)
async def simple_back_to_main(update, context):
    await handle_back_to_main(update, context)  # Використовуй загальний back
    return ConversationHandler.END

# forwarder to call entry_reports which is defined later in this file
async def call_entry_reports(update, context):
    return await entry_reports(update, context)

conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("menu", start),
        MessageHandler(filters.Regex(r"^(📊 Звіти)$"), call_entry_reports), # <-- Це правильно, обробляє кнопку Звіти
    ],  # Залишаємо, якщо handle_callback обробляє simplified entry
    states={
        WAITING_SIMPLE_DATE: [
            CallbackQueryHandler(handle_simple_date),
            CallbackQueryHandler(simple_back_to_main, pattern="^back_main$")
        ],
        WAITING_SIMPLE_MANUAL_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_simple_manual_date),
            CallbackQueryHandler(simple_back_to_main, pattern="^back_main$")
        ],
        WAITING_SIMPLE_PERIOD: [
            CallbackQueryHandler(handle_simple_period),
            CallbackQueryHandler(simple_back_to_main, pattern="^back_main$")
        ],
        WAITING_SIMPLE_SUBCATEGORY: [
            CallbackQueryHandler(handle_simple_subcategory),
            CallbackQueryHandler(simple_back_to_main, pattern="^back_main$")
        ],
        WAITING_SIMPLE_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_simple_amount),
            CallbackQueryHandler(simple_back_to_main, pattern="^back_main$")
        ],
        WAITING_SIMPLE_COMMENT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_simple_comment),
            CallbackQueryHandler(simple_back_to_main, pattern="^back_main$")
        ],
    },
    fallbacks=[CommandHandler('start', start)],
    per_chat=True,
    per_message=False,
)

# --- Основний flow для витрат: entry_points тепер використовують специфічні функції, що повертають стан
async def entry_add_expense(update, context):
    """Entry для додавання витрати — показує меню дати та повертає стан"""
    return await ask_expense_date(update, context)  # ask_expense_date повертає WAITING_EXPENSE_DATE

expense_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex(r"^➕ Додати витрату$"), ask_expense_date),
        CallbackQueryHandler(entry_add_expense, pattern="^add_expense$"),
        # Якщо є текстовий entry: MessageHandler(filters.Regex(r"(?i)додати витрату"), entry_add_expense)
    ],
    states={
        WAITING_EXPENSE_DATE: [
            CallbackQueryHandler(handle_expense_date_selection, pattern="^(date_today|date_yesterday|date_manual|back_main)$"),
        ],
        WAITING_MANUAL_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_date_input),
        ],
        WAITING_EXPENSE_TYPE: [
            CallbackQueryHandler(handle_expense_type_selection, pattern="^(expense_type_dividends|expense_type_other)$"),  # Специфічний handler для типу
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],

        WAITING_PERIOD: [
            CallbackQueryHandler(handle_period_selection, pattern="^period_"),
            # Обробник Назад
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"), 
        ],
        
        WAITING_LOCATION: [
            CallbackQueryHandler(handle_location_selection, pattern="^location_"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        
        WAITING_CHANGE: [
            # CallbackQueryHandler(handle_change_selection, pattern="^change_"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        
        WAITING_CATEGORY: [
            # CallbackQueryHandler(handle_category_selection, pattern="^category_"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        WAITING_EXPENSE_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_expense_input),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],
        # Якщо є інші стани як WAITING_PERIOD тощо, додай сюди аналогічно
        # WAITING_PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, your_period_handler)],  # Приклад — заміни на реальний
        # ... аналогічно для WAITING_LOCATION, WAITING_CHANGE, WAITING_CATEGORY тощо
    },
    fallbacks=[
        CommandHandler('start', start),
        CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
    ],
    per_chat=True,
    per_message=False,
)

# --- Звіти: entry показує меню, потім states обробляють вибір типу звіту
async def entry_reports(update, context):
    """Entry для звітів — показує меню вибору типу звіту"""
    await send_reports_menu(update)  # Показує inline з reports_owner/reports_fop (або div/other)
    return None  # Не повертаємо стан одразу — наступний callback перейде в states

report_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(entry_reports, pattern="^(reports_div|reports_other)$"),  # Або MessageHandler для тексту "звіти"
        # MessageHandler(filters.Regex(r"(?i)звіти"), entry_reports)
    ],
    states={
        # Додай стан для меню звітів, якщо потрібно (наприклад, WAITING_REPORT_TYPE)
        # Але припустимо, що start_report_owner/fop повертають WAITING_REPORT_OWNER/FOP
        WAITING_REPORT_OWNER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_report_owner),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],
        WAITING_REPORT_FOP: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_report_fop),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],
    },
    fallbacks=[
        CommandHandler('start', start),
        CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
    ],
    per_chat=True,
    per_message=False,
)