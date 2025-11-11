import datetime
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    WAITING_EXPENSE_DATE, WAITING_MANUAL_DATE, WAITING_EXPENSE_TYPE, WAITING_EXPENSE_INPUT,
    WAITING_PERIOD, WAITING_LOCATION, WAITING_CHANGE, WAITING_CATEGORY,
    WAITING_SUBCATEGORY, WAITING_PERSON_NAME, WAITING_ACCOUNT_SELECTION,
    CONFIG_OTHER, SUB_ASCII_TO_UKR,  SUBSUB_UKR_TO_ASCII,  WAITING_SUBSUBCATEGORY, CHANGE_ASCII_TO_UKR, CAT_ASCII_TO_UKR, CAT_UKR_TO_ASCII, SUB_UKR_TO_ASCII, WAITING_ACCOUNT_INPUT,ACCOUNT_MAP
) 
from sheets import add_expense_to_sheet, parse_expense, parse_expense_simple
from handlers.utils import send_main_menu, handle_back_to_main

# --- Обробка дати ---
async def ask_expense_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Сьогодні", callback_data="date_today")],
        [InlineKeyboardButton("📆 Вчора", callback_data="date_yesterday")],
        [InlineKeyboardButton("✏️ Ввести дату", callback_data="date_manual")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.message.edit_text("📆 Оберіть дату операції:", reply_markup=reply_markup)
        await update.callback_query.answer()
    else:
        await update.message.reply_text("📆 Оберіть дату операції:", reply_markup=reply_markup)
    return WAITING_EXPENSE_DATE

async def handle_expense_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "date_today":
        selected_date = datetime.datetime.now().strftime("%d.%m.%Y")
    elif query.data == "date_yesterday":
        selected_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
    elif query.data == "date_manual":
        await query.message.edit_text("📝 Введіть дату (ДД.ММ.РРРР):")
        return WAITING_MANUAL_DATE
    elif query.data == "back_main":
        return await handle_back_to_main(update, context)
    else:
        return await handle_back_to_main(update, context)
    return await show_expense_type_selection(update, context, selected_date)

async def handle_manual_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.datetime.strptime(text, "%d.%m.%Y")
        selected_date = text
        return await show_expense_type_selection(update, context, selected_date)
    except ValueError:
        await update.message.reply_text("⚠️ Невірний формат. Приклад: `04.11.2025`", parse_mode='Markdown')
        return WAITING_MANUAL_DATE

# --- Тип витрат ---
async def show_expense_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, selected_date: str):
    context.user_data["selected_date"] = selected_date
    keyboard = [
        [InlineKeyboardButton("💰 Dividends", callback_data="expense_type_dividends")],
        [InlineKeyboardButton("📈 Other Expenses", callback_data="expense_type_other")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"📅 Дата: **{selected_date}**\n\nОберіть тип:"
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return WAITING_EXPENSE_TYPE

async def handle_expense_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    expense_type = query.data.split('_')[-1]
    context.user_data['expense_type'] = expense_type
    
    if expense_type == 'dividends':
        await query.message.edit_text(
            "✅ **Dividends**\n\n📝 Введіть: `СУМА ФОП Ім'я` (напр. `2000 ФОП2 Ваня`):",
            parse_mode='Markdown'
        )
        return WAITING_EXPENSE_INPUT
        
    elif expense_type == 'other':
        # Починаємо з вибору Періоду
        keyboard = [[InlineKeyboardButton(v, callback_data=f"period_{k}")] for k, v in CONFIG_OTHER['periods'].items()]
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("📆 Оберіть період:", reply_markup=reply_markup)
        return WAITING_PERIOD

# --- Покроковий вибір для 'other' ---
async def handle_period_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    period_key = query.data.split('_', 1)[-1]
    context.user_data['period'] = CONFIG_OTHER['periods'][period_key]
    
    locations = CONFIG_OTHER['locations_by_period'][period_key]
    keyboard = [[InlineKeyboardButton(CONFIG_OTHER['locations'][loc], callback_data=f"location_{loc}")] for loc in locations]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("📍 Оберіть локацію:", reply_markup=reply_markup)
    return WAITING_LOCATION

async def handle_location_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    location_key = query.data.split('_', 1)[-1]
    context.user_data['location'] = CONFIG_OTHER['locations'][location_key]
    
    changes = CONFIG_OTHER['changes_by_location_period'][context.user_data.get('period_key', 'lito_2025')][location_key]
    keyboard = [[InlineKeyboardButton(CHANGE_ASCII_TO_UKR[ch], callback_data=f"change_{ch}")] for ch in changes]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("👥 Оберіть зміну/особу:", reply_markup=reply_markup)
    return WAITING_CHANGE

async def handle_change_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    change_key = query.data.split('_', 1)[-1]
    context.user_data['change'] = CHANGE_ASCII_TO_UKR[change_key]
    
    categories_list = CONFIG_OTHER['categories_by_change'][context.user_data['change']]
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"category_{CAT_UKR_TO_ASCII.get(cat, cat.lower().replace(' ', '_'))}")] for cat in categories_list]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("📑 Оберіть категорію:", reply_markup=reply_markup)
    return WAITING_CATEGORY

async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_key = query.data.split('_', 1)[-1]
    cat_name = CAT_ASCII_TO_UKR.get(cat_key, cat_key)
    context.user_data['category'] = cat_name
    
    subcats = CONFIG_OTHER['subcategories_by_category'].get(cat_key, [])
    if not subcats:
        await query.message.edit_text(f"✅ Категорія: **{cat_name}**\n\n💰 Введіть суму та опис:", parse_mode='Markdown')
        return WAITING_EXPENSE_INPUT
    
    keyboard = [
        [InlineKeyboardButton(sub, callback_data=f"subcategory_{SUB_UKR_TO_ASCII.get(sub, sub)}")]
        for sub in subcats
    ]

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(f"📂 Підкатегорія для '{cat_name}':", reply_markup=reply_markup)
    return WAITING_SUBCATEGORY

# --- Вибір підкатегорії з особливістю для "Тех. працівники" ---
# --- Вибір підкатегорії ---
async def handle_subcategory_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Отримуємо ключ підкатегорії (ASCII)
    subcat_key = query.data.split('_', 1)[-1]
    
    # Перетворюємо ASCII у нормальну українську назву
    subcat_name = SUB_ASCII_TO_UKR.get(subcat_key, subcat_key)
    
    # Зберігаємо підкатегорію у контекст
    context.user_data['subcategory'] = subcat_name

    # 🧩 Якщо вибрано "Тех. працівники" — показуємо вибір особи
    if subcat_name == "Тех. працівники":
        keyboard = [
            [InlineKeyboardButton("Олег", callback_data="person_oleg")],
            [InlineKeyboardButton("Леся", callback_data="person_lesya")],
            [InlineKeyboardButton("Вова", callback_data="person_vova")],
            [InlineKeyboardButton("Інший", callback_data="person_other")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("👤 Оберіть працівника або введіть ім'я:", reply_markup=reply_markup)
        return WAITING_PERSON_NAME

    # 🔁 Якщо є під-підкатегорії (наприклад, для “Відділ продажів”)
    if subcat_key in CONFIG_OTHER.get('subsubcategories_by_category', {}):
        subsubs = CONFIG_OTHER['subsubcategories_by_category'][subcat_key]
        keyboard = [
            [InlineKeyboardButton(subsub, callback_data=f"subsubcategory_{SUBSUB_UKR_TO_ASCII.get(subsub, subsub)}")]
            for subsub in subsubs
        ]
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(f"📂 Оберіть підкатегорію для '{subcat_name}':", reply_markup=reply_markup)
        return WAITING_SUBSUBCATEGORY

    # 🧾 Інакше переходимо далі до вибору ФОПа
    return await ask_account_selection(update, context)


# --- Введення імені вручну або вибір ---
async def handle_person_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "person_other":
        await query.message.edit_text("👤 Введіть ім'я працівника:")
        return WAITING_PERSON_NAME
    else:
        person_map = {"oleg": "Олег", "lesya": "Леся", "vova": "Вова"}
        person_key = query.data.split('_', 1)[-1]
        context.user_data['person'] = person_map.get(person_key, person_key)
        return await ask_account_selection(update, context)

async def handle_manual_person_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['person'] = update.message.text.strip()
    return await ask_account_selection(update, context)

# --- Вибір ФОПа ---
async def ask_account_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("ФОП №1 Радул І.І.", callback_data="account_1")],
        [InlineKeyboardButton("ФОП №2 Радул Я.Ю.", callback_data="account_2")],
        [InlineKeyboardButton("ФОП №3 Скидан Х.С.", callback_data="account_3")],
        [InlineKeyboardButton("Інший", callback_data="account_other")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "💼 Оберіть ФОП:"
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)
    return WAITING_ACCOUNT_SELECTION

async def handle_account_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "account_other":
        await query.message.edit_text("💼 Введіть назву ФОПа:")
        return WAITING_ACCOUNT_INPUT
    else:
        account_key = query.data.split('_', 1)[-1]
        context.user_data['account'] = ACCOUNT_MAP.get(account_key, f"ФОП №{account_key}")
        await query.message.edit_text("💰 Введіть суму та опис (напр. `15000 ЗП Вова`):")
        return WAITING_EXPENSE_INPUT

async def handle_account_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['account'] = update.message.text.strip()
    await update.message.reply_text("💰 Введіть суму та опис (напр. `15000 ЗП Вова`):")
    return WAITING_EXPENSE_INPUT

# --- Обробка суми ---
async def process_expense_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    expense_type = context.user_data.get('expense_type', 'dividends')
    selected_date = context.user_data.get('selected_date', datetime.datetime.now().strftime("%d.%m.%Y"))

    if expense_type == 'dividends':
        parsed = parse_expense(text)
    else:
        parsed = parse_expense_simple(text)

    if parsed and 'сума' in parsed:
        try:
            parsed['Дата'] = selected_date
            add_expense_to_sheet(parsed, context.user_data, expense_type)

            # Формуємо підтвердження
            msg = f"✅ Додано в **{expense_type.upper()}**!\n"
            msg += f"**Дата**: {selected_date}\n"
            if expense_type == 'other':
                msg += f"**Період**: {context.user_data.get('period', '—')}\n"
                msg += f"**Локація**: {context.user_data.get('location', '—')}\n"
                msg += f"**Зміна**: {context.user_data.get('change', '—')}\n"
                msg += f"**Категорія**: {context.user_data.get('category', '—')}\n"
                msg += f"**Підкатегорія**: {context.user_data.get('subcategory', '—')}\n"
                if 'person' in context.user_data:
                    msg += f"**Працівник**: {context.user_data['person']}\n"
                if 'account' in context.user_data:
                    msg += f"**ФОП**: {context.user_data['account']}\n"
            msg += f"**Сума**: {parsed['сума']} грн"
            if parsed.get('коментар'):
                msg += f"\n**Коментар**: {parsed['коментар']}"

            await update.message.reply_text(msg, parse_mode='Markdown')
        except Exception as e:
            logging.error(f"❌ Помилка запису: {e}")
            await update.message.reply_text("❌ Помилка запису. Спробуйте ще раз.")
            return WAITING_EXPENSE_INPUT
    else:
        await update.message.reply_text("⚠️ Невірний формат. Спробуйте: `СУМА ОПИС`")
        return WAITING_EXPENSE_INPUT

    context.user_data.clear()
    await send_main_menu(update, context, "Операція завершена.")
    return ConversationHandler.END

async def handle_subsubcategory_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    subsub_key = query.data.split('_', 1)[-1]
    context.user_data['subsubcategory'] = subsub_key

    # Якщо є ще глибші рівні — тут можна буде додати додаткову логіку
    await query.message.edit_text(
        f"✅ Обрано: **{subsub_key}**\n\n💼 Тепер оберіть ФОПа:",
        parse_mode='Markdown'
    )

    return await ask_account_selection(update, context)

