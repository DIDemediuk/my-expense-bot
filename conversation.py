from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from handlers.main_handler import start, handle_message, handle_callback  # Додав handle_callback для conv_handler
from handlers.expense_handler import (
    ask_expense_date, handle_expense_date_selection, handle_manual_date_input,
    handle_expense_type_selection, process_expense_input, handle_back_to_main
)
from handlers.report_handler import (
    send_reports_menu, start_report_owner, start_report_fop, process_report_owner, process_report_fop
)
from config import (
    WAITING_EXPENSE_TYPE, WAITING_PERIOD, WAITING_LOCATION, WAITING_CHANGE,
    WAITING_CATEGORY, WAITING_SUBCATEGORY, WAITING_SUBSUBCATEGORY, WAITING_EXPENSE_INPUT,
    WAITING_EXPENSE_DATE, WAITING_MANUAL_DATE, WAITING_REPORT_OWNER, WAITING_REPORT_FOP
)

# --- simplified (додаємо back_main fallback)
try:
    from handlers.simplified_expense import (
        WAITING_SIMPLE_DATE, WAITING_SIMPLE_MANUAL_DATE, WAITING_SIMPLE_PERIOD,
        WAITING_SIMPLE_SUBCATEGORY, WAITING_SIMPLE_AMOUNT, WAITING_SIMPLE_COMMENT,
        handle_simple_date, handle_simple_manual_date, handle_simple_period,
        handle_simple_subcategory, handle_simple_amount, handle_simple_comment
    )
except ImportError:
    # Цей блок повинен бути з відступами (4 пробіли)
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
    async def WAITING_REPORT_TYPE(update, context): pass


async def simple_back_to_main(update, context):
    await handle_back_to_main(update, context)
    return ConversationHandler.END


conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_callback)],  # Якщо handle_callback обробляє simplified
    states={
        WAITING_SIMPLE_DATE: [
            CallbackQueryHandler(handle_simple_date, pattern="^(simple_date_.*|back_main)$"),
            CallbackQueryHandler(simple_back_to_main, pattern="^back_main$")
        ],
        WAITING_SIMPLE_MANUAL_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_simple_manual_date),
            CallbackQueryHandler(simple_back_to_main, pattern="^back_main$")
        ],
        # ... аналогічно для інших simple станів з pattern та back_main
        WAITING_SIMPLE_PERIOD: [
            CallbackQueryHandler(handle_simple_period, pattern="^(simple_period_.*|back_main)$"),
            CallbackQueryHandler(simple_back_to_main, pattern="^back_main$")
        ],
        WAITING_SIMPLE_SUBCATEGORY: [
            CallbackQueryHandler(handle_simple_subcategory, pattern="^(simple_subcat_.*|back_main)$"),
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

# --- Заглушки для нереалізованих handlers (щоб уникнути Pylance помилок) ---
# Ці функції можна реалізувати пізніше в expense_handler.py
async def handle_period_selection(update, context):
    """Заглушка для WAITING_PERIOD — реалізуй логіку вибору періоду"""
    await update.message.reply_text("⚠️ Функція періоду в розробці. Повертаємо назад.")
    await handle_back_to_main(update, context)
    return ConversationHandler.END

async def handle_location_input(update, context):
    """Заглушка для WAITING_LOCATION — реалізуй введення локації"""
    await update.message.reply_text("⚠️ Функція локації в розробці. Повертаємо назад.")
    await handle_back_to_main(update, context)
    return ConversationHandler.END

async def handle_change_input(update, context):
    """Заглушка для WAITING_CHANGE — реалізуй введення зміни"""
    await update.message.reply_text("⚠️ Функція зміни в розробці. Повертаємо назад.")
    await handle_back_to_main(update, context)
    return ConversationHandler.END

async def handle_category_selection(update, context):
    """Заглушка для WAITING_CATEGORY — реалізуй вибір категорії (inline)"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.message.reply_text("⚠️ Вибір категорії в розробці. Повертаємо назад.")
    await handle_back_to_main(update, context)
    return ConversationHandler.END

async def handle_subcategory_selection(update, context):
    """Заглушка для WAITING_SUBCATEGORY — реалізуй вибір підкатегорії"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.message.reply_text("⚠️ Вибір підкатегорії в розробці. Повертаємо назад.")
    await handle_back_to_main(update, context)
    return ConversationHandler.END

async def handle_subsubcategory_selection(update, context):
    """Заглушка для WAITING_SUBSUBCATEGORY — реалізуй вибір підпідкатегорії"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.message.reply_text("⚠️ Вибір підпідкатегорії в розробці. Повертаємо назад.")
    await handle_back_to_main(update, context)
    return ConversationHandler.END

# --- Основний flow для витрат: додаємо ТЕКСТОВИЙ entry_point для "Додати витрату"
expense_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex(r"(?i)(➕ )?додати витрату"), ask_expense_date),  # Текстове меню + емодзі
        CallbackQueryHandler(ask_expense_date, pattern="^add_expense$"),  # Для inline, якщо є
    ],
    states={
        WAITING_EXPENSE_DATE: [
            CallbackQueryHandler(handle_expense_date_selection, pattern="^(date_today|date_yesterday|date_manual|back_main)$"),
            # Додай MessageHandler, якщо хочеш дозволити текст у цьому стані (але зазвичай inline)
        ],
        WAITING_MANUAL_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_date_input),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")  # Якщо з'явиться inline тут
        ],
        WAITING_EXPENSE_TYPE: [
            CallbackQueryHandler(handle_expense_type_selection, pattern="^(expense_type_dividends|expense_type_other)$"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],
        WAITING_EXPENSE_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_expense_input),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],
        # Додай інші стани з config, якщо вони використовуються в expense flow
        WAITING_PERIOD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_period_selection),  # Тепер визначено
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],
        WAITING_LOCATION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_location_input),  # Тепер визначено
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],
        WAITING_CHANGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_change_input),  # Тепер визначено
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],
        WAITING_CATEGORY: [
            CallbackQueryHandler(handle_category_selection, pattern="^category_.*$"),  # Тепер визначено
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],
        WAITING_SUBCATEGORY: [
            CallbackQueryHandler(handle_subcategory_selection, pattern="^subcategory_.*$"),  # Тепер визначено
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],
        WAITING_SUBSUBCATEGORY: [
            CallbackQueryHandler(handle_subsubcategory_selection, pattern="^subsubcategory_.*$"),  # Тепер визначено
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],
    },
    fallbacks=[
        CommandHandler('start', start),
        CallbackQueryHandler(handle_back_to_main, pattern="^back_main$"),
        MessageHandler(filters.Regex(r"(?i)(назад|закрити)"), handle_back_to_main)  # Текстовий back
    ],
    per_chat=True,
    per_message=False,
    allow_reentry=True  # Дозволяє перезапуск без /start
)

# --- Звіти: додаємо текстовий entry та стан для меню
report_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex(r"(?i)(📊 )?звіти"), send_reports_menu),  # Текстове меню
        CallbackQueryHandler(send_reports_menu, pattern="^(reports_div|reports_other)$"),
    ],
    states={
        # Додаємо стан для вибору типу звіту (після send_reports_menu)
        WAITING_REPORT_TYPE: [  # Новий стан для inline меню owner/fop
            CallbackQueryHandler(start_report_owner, pattern="^reports_owner$"),
            CallbackQueryHandler(start_report_fop, pattern="^reports_fop$"),
            CallbackQueryHandler(handle_back_to_main, pattern="^back_main$")
        ],
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
    allow_reentry=True
)