from telegram.ext import ContextTypes
from config import CONFIG_OTHER

# Стани
WAITING_SIMPLE_DATE = 1001
WAITING_SIMPLE_MANUAL_DATE = 1002
WAITING_SIMPLE_PERIOD = 1003
WAITING_SIMPLE_SUBCATEGORY = 1004
WAITING_SIMPLE_AMOUNT = 1005
WAITING_SIMPLE_COMMENT = 1006

# Ролі користувачів
USER_ROLES = []  # Додайте ID користувачів

async def simplified_expense_flow(update, context, user_id):
    await update.callback_query.message.reply_text("Спрощений потік запущено...")
    return WAITING_SIMPLE_DATE

async def handle_simple_date(update, context):
    pass

async def handle_simple_manual_date(update, context):
    pass

async def handle_simple_period(update, context):
    pass

async def handle_simple_subcategory(update, context):
    pass

async def handle_simple_amount(update, context):
    pass

async def handle_simple_comment(update, context):
    pass