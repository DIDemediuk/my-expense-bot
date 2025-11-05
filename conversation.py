# conversation.py (ПОВНИЙ РОБОЧИЙ КОД)
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from handlers.main_handler import start, handle_message, handle_callback
from handlers.expense_handler import (
    ask_expense_date, handle_expense_date_selection, handle_manual_date_input,
    handle_expense_type_selection, process_expense_input,
    # ✅ НОВІ ФУНКЦІЇ ДЛЯ ПОКРОКОВОГО ВВОДУ
    handle_period_selection, handle_location_selection, handle_change_selection,
    handle_subcategory_selection, handle_subsubcategory_selection, handle_category_selection
    # Всі handle_back_to_main тепер імпортуються з handlers.utils!
)
from handlers.report_handler import (
    send_reports_menu, start_report_owner, start_report_fop, 
    process_report_owner, process_report_fop # ✅ ФІКС process_report_owner (NameError)
) 
from handlers.utils import handle_back_to_main # ✅ ФІКС ЦИКЛІЧНОГО ІМПОРТУ
from config import (
    WAITING_EXPENSE_TYPE, WAITING_PERIOD, WAITING_LOCATION, WAITING_CHANGE,
    WAITING_CATEGORY, WAITING_SUBCATEGORY, WAITING_SUBSUBCATEGORY, WAITING_EXPENSE_INPUT,
    WAITING_EXPENSE_DATE, WAITING_MANUAL_DATE, WAITING_REPORT_OWNER, WAITING_REPORT_FOP
)

# --- simplified (залишаємо як є) ---
# ... (ваш існуючий код для simplified) ...

conv_handler = ConversationHandler( 
    entry_points=[
        # Наприклад, CommandHandler('menu', handle_menu)
        CommandHandler('start', start) # Додайте стартову команду, якщо це головний хендлер
    ],
    states={
        # Якщо він не має станів, можна залишити порожнім, але він повинен бути.
    },
    fallbacks=[
        CommandHandler('help', start) # або інший обробник
    ],
    # ... (ваш існуючий код для conv_handler) ...
    per_chat=True,
    per_message=False,
)

expense_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex(r"^➕ Додати витрату$"), ask_expense_date),
        CallbackQueryHandler(ask_expense_date, pattern="^(add_expense)$") 
    ],
    states={
        WAITING_EXPENSE_DATE: [
            CallbackQueryHandler(handle_expense_date_selection, pattern="^(date_today|date_yesterday|date_manual|back_main)$")
        ],
        WAITING_MANUAL_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_date_input)
        ],
        WAITING_EXPENSE_TYPE: [
            CallbackQueryHandler(handle_expense_type_selection, pattern="^(expense_type_dividends|expense_type_other|back_main)$")
        ],
        # ✅ НОВІ СТАНИ ДЛЯ OTHER EXPENSES
        WAITING_PERIOD: [
            CallbackQueryHandler(handle_period_selection, pattern="^period_"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"), 
        ],
        WAITING_LOCATION: [
            CallbackQueryHandler(handle_location_selection, pattern="^location_"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        WAITING_CHANGE: [
            CallbackQueryHandler(handle_change_selection, pattern="^change_"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        WAITING_CATEGORY: [
            CallbackQueryHandler(handle_category_selection, pattern="^category_.*$"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        WAITING_SUBCATEGORY: [
            CallbackQueryHandler(handle_subcategory_selection, pattern="^subcategory_.*$"),  # ✅ Додати
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        WAITING_SUBSUBCATEGORY: [
            CallbackQueryHandler(handle_subsubcategory_selection, pattern="^subsubcategory_.*$"),  # ✅ Додати
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        
        WAITING_EXPENSE_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_expense_input)
        ],
    },
    fallbacks=[
        CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
    ],
    per_chat=True,
    per_message=False,
)

# --- Звіти ---
async def entry_reports(update, context):
    await send_reports_menu(update)
    return None

report_conv = ConversationHandler(
    entry_points=[
        # Припускаємо, що reports викликається через callback або команду
        MessageHandler(filters.Regex(r"📊 Звіти"), entry_reports),
        CallbackQueryHandler(start_report_owner, pattern="^reports_owner$"),
        CallbackQueryHandler(start_report_fop, pattern="^reports_fop$"),
    ],
    states={
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
        CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
    ],
    per_chat=True,
    per_message=False,
)