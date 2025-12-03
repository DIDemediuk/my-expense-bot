# conversation.py (ПОВНИЙ РОБОЧИЙ КОД)
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from handlers.main_handler import start, handle_message, handle_callback
from handlers.expense_handler import (
    ask_expense_date, handle_expense_date_selection, handle_manual_date_input,
    handle_expense_type_selection, process_expense_input,
    handle_period_selection, handle_location_selection, handle_change_selection,
    handle_category_selection, handle_subcategory_selection,
    handle_person_selection, handle_manual_person_input,
    ask_account_selection, handle_account_selection, handle_account_input, handle_subsubcategory_selection, WAITING_SUBCATEGORY,
    handle_dividends_owner_selection, handle_dividends_category_selection,
    handle_dividends_account_selection, handle_dividends_amount_input
)
# --- Додаємо імпорт для simplified_expense ---
from handlers.simplified_expense import (
    simplified_expense_flow,
    handle_simple_date,
    handle_simple_manual_date,
    handle_simple_period,
    handle_simple_subcategory,
    handle_simple_amount,
    handle_simple_comment,
    WAITING_SIMPLE_DATE,
    WAITING_SIMPLE_MANUAL_DATE,
    WAITING_SIMPLE_PERIOD,
    WAITING_SIMPLE_SUBCATEGORY,
    WAITING_SIMPLE_AMOUNT,
    WAITING_SIMPLE_COMMENT
)
from handlers.report_handler import (
    send_reports_menu, start_report_owner, start_report_fop, 
    process_report_owner, process_report_fop # ✅ ФІКС process_report_owner (NameError)
) 
from handlers.utils import handle_back_to_main # ✅ ФІКС ЦИКЛІЧНОГО ІМПОРТУ
from config import (
    WAITING_EXPENSE_TYPE, WAITING_PERIOD, WAITING_LOCATION, WAITING_CHANGE,
    WAITING_CATEGORY, WAITING_SUBSUBCATEGORY, WAITING_EXPENSE_INPUT,
    WAITING_EXPENSE_DATE, WAITING_MANUAL_DATE, WAITING_REPORT_OWNER, WAITING_REPORT_FOP,
    WAITING_PERSON_NAME,
    WAITING_ACCOUNT_SELECTION,
    WAITING_ACCOUNT_INPUT,
    WAITING_DIVIDENDS_OWNER, WAITING_DIVIDENDS_CATEGORY,
    WAITING_DIVIDENDS_ACCOUNT, WAITING_DIVIDENDS_AMOUNT
)



# --- ConversationHandler для simplified_expense_flow ---
simplified_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(simplified_expense_flow, pattern="^add_expense_simple$")],
    states={
        WAITING_SIMPLE_DATE: [CallbackQueryHandler(handle_simple_date)],
        WAITING_SIMPLE_MANUAL_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_simple_manual_date)],
        WAITING_SIMPLE_PERIOD: [CallbackQueryHandler(handle_simple_period)],
        WAITING_SIMPLE_SUBCATEGORY: [CallbackQueryHandler(handle_simple_subcategory)],
        WAITING_SIMPLE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_simple_amount)],
        WAITING_SIMPLE_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_simple_comment)],
    },
    fallbacks=[CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")],
    per_chat=True,
    per_message=False,
)

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
        # Стани для Dividends
        WAITING_DIVIDENDS_OWNER: [
            CallbackQueryHandler(handle_dividends_owner_selection, pattern="^(dividends_owner_|back_main$)"),
        ],
        WAITING_DIVIDENDS_CATEGORY: [
            CallbackQueryHandler(handle_dividends_category_selection, pattern="^(dividends_category_|back_main$)"),
        ],
        WAITING_DIVIDENDS_ACCOUNT: [
            CallbackQueryHandler(handle_dividends_account_selection, pattern="^(dividends_account_|back_main$)"),
        ],
        WAITING_DIVIDENDS_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dividends_amount_input),
        ],

        WAITING_PERIOD: [
            CallbackQueryHandler(handle_period_selection, pattern="^(period_|back_to_type)"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        WAITING_LOCATION: [
            CallbackQueryHandler(handle_location_selection, pattern="^(location_|back_to_period)"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        WAITING_CHANGE: [
            CallbackQueryHandler(handle_change_selection, pattern="^(change_|back_to_location)"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        WAITING_CATEGORY: [
            CallbackQueryHandler(handle_category_selection, pattern="^(category_.*|back_to_change)$"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        WAITING_SUBCATEGORY: [
            CallbackQueryHandler(handle_subcategory_selection, pattern="^(subcategory_.*|back_to_category)$"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        WAITING_SUBSUBCATEGORY: [  # 🧩 додано
            CallbackQueryHandler(handle_subsubcategory_selection, pattern="^(subsubcategory_.*|back_to_subcategory)$"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        WAITING_PERSON_NAME: [
            CallbackQueryHandler(handle_person_selection, pattern="^person_.*$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_person_input),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        WAITING_ACCOUNT_SELECTION: [
            CallbackQueryHandler(handle_account_selection, pattern="^account_.*$"),  # ✅ фікс
            CallbackQueryHandler(handle_subsubcategory_selection, pattern="^back_to_subcategory$"),
            CallbackQueryHandler(handle_subcategory_selection, pattern="^back_to_category$"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        WAITING_ACCOUNT_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_account_input),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        ],
        # WAITING_ACCOUNT_INPUT також використовується для dividends при введенні ФОПа вручну
        WAITING_EXPENSE_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_expense_input)
        ],
    },
    fallbacks=[
        CommandHandler('start', handle_back_to_main),
        CommandHandler('cancel', handle_back_to_main),
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