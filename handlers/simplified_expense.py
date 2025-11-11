from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import CONFIG_OTHER
from sheets import add_expense_to_sheet

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
    # Вибір періоду (літо/осінь/зима)
    keyboard = [
        [InlineKeyboardButton(v, callback_data=f"simple_period_{k}")] for k, v in CONFIG_OTHER['periods'].items()
    ]
    await update.callback_query.message.reply_text(
        "Оберіть період:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_SIMPLE_PERIOD

async def handle_simple_manual_date(update, context):
    # Введення дати вручну (можна додати перевірку формату)
    text = update.message.text.strip()
    context.user_data['date'] = text
    # Далі - вибір періоду
    keyboard = [
        [InlineKeyboardButton(v, callback_data=f"simple_period_{k}")] for k, v in CONFIG_OTHER['periods'].items()
    ]
    await update.message.reply_text(
        "Оберіть період:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_SIMPLE_PERIOD

async def handle_simple_period(update, context):
    # Зберігаємо вибраний період
    query = update.callback_query
    period_key = query.data.replace("simple_period_", "")
    context.user_data['period'] = CONFIG_OTHER['periods'][period_key]
    # Далі - вибір підкатегорії (наприклад, для тесту - просто список)
    subcategories = ["Їжа", "Транспорт", "Матеріали", "Інше"]
    keyboard = [[InlineKeyboardButton(sub, callback_data=f"simple_subcat_{i}")] for i, sub in enumerate(subcategories)]
    await query.message.reply_text(
        "Оберіть підкатегорію:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['subcategories'] = subcategories
    return WAITING_SIMPLE_SUBCATEGORY

async def handle_simple_subcategory(update, context):
    query = update.callback_query
    idx = int(query.data.replace("simple_subcat_", ""))
    subcat = context.user_data.get('subcategories', [])[idx]
    context.user_data['subcategory'] = subcat
    # Далі - введення суми
    await query.message.reply_text("Введіть суму витрати (наприклад, 1500):")
    return WAITING_SIMPLE_AMOUNT

async def handle_simple_amount(update, context):
    text = update.message.text.strip()
    try:
        amount = float(text.replace(',', '.'))
    except Exception:
        await update.message.reply_text("❗️ Введіть коректну суму (наприклад, 1500 або 1500.50)")
        return WAITING_SIMPLE_AMOUNT
    context.user_data['amount'] = amount
    # Далі - коментар (опціонально)
    await update.message.reply_text("Додайте коментар або натисніть /skip, якщо не потрібно:")
    return WAITING_SIMPLE_COMMENT

async def handle_simple_comment(update, context):
    text = update.message.text.strip()
    context.user_data['comment'] = text
    # Формуємо дані для запису
    parsed = {
        "рахунок": "Готівка",  # або інший спосіб визначення рахунку
        "сума": context.user_data.get('amount'),
        "коментар": context.user_data.get('comment', '')
    }
    try:
        add_expense_to_sheet(parsed, context.user_data, expense_type='other')
        await update.message.reply_text(
            f"✅ Запис збережено!\nПеріод: {context.user_data.get('period')}\nПідкатегорія: {context.user_data.get('subcategory')}\nСума: {context.user_data.get('amount')}\nКоментар: {context.user_data.get('comment', '')}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Помилка запису у таблицю: {e}")
    context.user_data.clear()
    return -1  # Кінець розмови