# handlers/expense_handler.py (Доповнений: додані handlers для category/subcategory)
import datetime
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    WAITING_EXPENSE_DATE, WAITING_MANUAL_DATE, WAITING_EXPENSE_TYPE, WAITING_EXPENSE_INPUT,
    WAITING_PERIOD, WAITING_LOCATION, WAITING_CHANGE, WAITING_CATEGORY,
    WAITING_SUBCATEGORY, WAITING_SUBSUBCATEGORY, CONFIG_OTHER,
    CHANGE_ASCII_TO_UKR, SUB_ASCII_TO_UKR, SUBSUB_ASCII_TO_UKR, CAT_ASCII_TO_UKR, CAT_UKR_TO_ASCII, SUB_UKR_TO_ASCII  # ✅ Додано зворотні мапінги для ключів
) 
from sheets import add_expense_to_sheet, parse_expense, parse_expense_simple
from handlers.utils import (
    send_main_menu, 
    ask_period_menu,  
    ask_location_menu,
    ask_change_menu,
    ask_category_menu,
    ask_subcategory_menu,
    ask_subsubcategory_menu,
    handle_back_to_main 
) 

# --- Функції обробки дати (ОК) ---

async def ask_expense_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Сьогодні", callback_data="date_today")],
        [InlineKeyboardButton("📆 Вчора", callback_data="date_yesterday")],
        [InlineKeyboardButton("✏️ Ввести дату вручну", callback_data="date_manual")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.message.edit_text("📆 Оберіть дату операції:", reply_markup=reply_markup)
        await update.callback_query.answer()
    elif update.message:
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
        await query.message.edit_text("📝 Введіть дату у форматі ДД.ММ.РРРР (наприклад, 27.10.2025):")
        return WAITING_MANUAL_DATE
    elif query.data == "back_main":
        return await handle_back_to_main(update, context)
    else:
        return
    return await show_expense_type_selection(update, context, selected_date)

async def handle_manual_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.datetime.strptime(text, "%d.%m.%Y")
        selected_date = text
        return await show_expense_type_selection(update, context, selected_date)
    except ValueError:
        await update.message.reply_text("⚠️ Невірний формат. Спробуйте ще раз (ДД.ММ.РРРР):")
        return WAITING_MANUAL_DATE

# --- Функції обробки типу витрат (КРИТИЧНА ЛОГІКА) ---

async def show_expense_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, selected_date: str):
    context.user_data["selected_date"] = selected_date
    keyboard = [
        [InlineKeyboardButton("💰 Dividends", callback_data="expense_type_dividends")],
        [InlineKeyboardButton("📈 Other Expenses", callback_data="expense_type_other")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"📅 Обрана дата: **{selected_date}**\n\nОбери тип:"
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return WAITING_EXPENSE_TYPE

async def handle_expense_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    expense_type = data.split('_')[-1]

    context.user_data['expense_type'] = expense_type
    
    if expense_type == 'dividends':
        # Для дивідендів одразу до введення
        await query.message.edit_text(
            f"✅ Тип: **{expense_type.upper()}**\n\n📝 Введіть деталі дивідендів (сума + джерело + власник, напр. '500 ФОП2 Яна'):",
            parse_mode='Markdown'
        )
        return WAITING_EXPENSE_INPUT
        
    elif expense_type == 'other':
        # ✅ Починаємо покроковий вибір з Періоду
        await ask_period_menu(update, context) 
        return WAITING_PERIOD

# --- НОВІ ОБРОБНИКИ ДЛЯ ПОКРОКОВОГО ВВОДУ ---

async def handle_period_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    period_key = query.data.split('_', 1)[-1] 
    period_name = CONFIG_OTHER['periods'].get(period_key, period_key)
    context.user_data['period_key'] = period_key  # ✅ Зберігаємо ключ
    context.user_data['period'] = period_name
    
    # Крок 2: Перехід до вибору Локації
    await ask_location_menu(update, context) 
    return WAITING_LOCATION 

async def handle_location_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    location_key = query.data.split('_', 1)[-1] 
    location_name = CONFIG_OTHER['locations'].get(location_key, location_key)
    context.user_data['location_key'] = location_key  # ✅ Зберігаємо ключ
    context.user_data['location'] = location_name
    
    # Крок 3: Перехід до вибору Зміни/Особи
    await ask_change_menu(update, context) 
    return WAITING_CHANGE 

async def handle_change_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    change_key = query.data.split('_', 1)[-1] 
    change_name = CHANGE_ASCII_TO_UKR.get(change_key, change_key)
    context.user_data['change_key'] = change_key  # ✅ Зберігаємо ключ
    context.user_data['change'] = change_name
    
    # ✅ ФІКС: Завантажуємо категорії динамічно на основі change_name (e.g. '1 - Зміна': ['Розваги', ...])
    categories_list = CONFIG_OTHER.get('categories_by_change', {}).get(change_name, [])  # List назв
    
    if not categories_list:
        logging.warning(f"⚠️ Категорії не знайдено для зміни '{change_name}'. Використовуємо загальні.")
        categories_list = ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору']  # Fallback
    
    # Мапимо назви в ключі для callback (CAT_UKR_TO_ASCII)
    category_keys = [CAT_UKR_TO_ASCII.get(cat, cat.lower().replace(' ', '_').replace('ї', 'i').replace('і', 'i')) for cat in categories_list]  # Адаптовано для укр. символів
    
    # Показуємо меню з назвами, callback з ключами
    keyboard = []
    current_row = []
    for i, cat_name in enumerate(categories_list):
        cat_key = category_keys[i]
        current_row.append(InlineKeyboardButton(cat_name, callback_data=f"category_{cat_key}"))
        if len(current_row) == 2:
            keyboard.append(current_row)
            current_row = []
    if current_row:
        keyboard.append(current_row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    prompt = f"📑 Оберіть **Категорію** (для зміни '{change_name}'):"
    
    await query.message.edit_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')
    return WAITING_CATEGORY

# ✅ НОВИЙ: Обробник для вибору Категорії
async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_key = query.data.split('_', 1)[-1] 
    cat_name = CAT_ASCII_TO_UKR.get(cat_key, cat_key)  # Мапінг зворотний для назви
    context.user_data['category_key'] = cat_key
    context.user_data['category'] = cat_name
    
    # ✅ ФІКС: Завантажуємо підкатегорії динамічно на основі cat_key (e.g. 'розваги': ['Гонорар', ...])
    subcats_list = CONFIG_OTHER.get('subcategories_by_category', {}).get(cat_key, [])  # List назв
    
    if not subcats_list:
        logging.warning(f"⚠️ Підкатегорії не знайдено для '{cat_name}'. Переходимо до введення.")
        await query.message.edit_text(
            f"✅ Категорія: **{cat_name}**\n\n📝 Введіть суму та опис (напр. '500 Бензин'):",
            parse_mode='Markdown'
        )
        return WAITING_EXPENSE_INPUT
    
    # Мапимо назви в ключі для callback (SUB_UKR_TO_ASCII)
    subcat_keys = [SUB_UKR_TO_ASCII.get(sub, sub.lower().replace(' ', '_').replace('ї', 'i').replace('і', 'i')) for sub in subcats_list]
    
    keyboard = []
    current_row = []
    for i, sub_name in enumerate(subcats_list):
        sub_key = subcat_keys[i]
        current_row.append(InlineKeyboardButton(sub_name, callback_data=f"subcategory_{sub_key}"))
        if len(current_row) == 2:
            keyboard.append(current_row)
            current_row = []
    if current_row:
        keyboard.append(current_row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    prompt = f"📂 Оберіть **Підкатегорію** (для '{cat_name}'):"
    
    await query.message.edit_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')
    return WAITING_SUBCATEGORY

# ✅ НОВИЙ: Обробник для вибору Підкатегорії
async def handle_subcategory_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subcat_key = query.data.split('_', 1)[-1] 
    subcat_name = SUB_ASCII_TO_UKR.get(subcat_key, subcat_key)  # З config
    context.user_data['subcategory_key'] = subcat_key
    context.user_data['subcategory'] = subcat_name
    
    # Крок 6: Перехід до вибору Підпідкатегорії (якщо потрібно)
    await ask_subsubcategory_menu(update, context)
    return WAITING_SUBSUBCATEGORY

# ✅ НОВИЙ: Обробник для вибору Підпідкатегорії
async def handle_subsubcategory_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subsub_key = query.data.split('_', 1)[-1] 
    subsub_name = SUBSUB_ASCII_TO_UKR.get(subsub_key, subsub_key)  # З config
    context.user_data['subsubcategory_key'] = subsub_key
    context.user_data['subsubcategory'] = subsub_name
    
    # Тепер до введення суми/коментаря
    await query.message.edit_text(
        f"✅ Підпідкатегорія: **{subsub_name}**\n\n📝 Введіть суму та опис (напр. '500 Бензин'):",
        parse_mode='Markdown'
    )
    return WAITING_EXPENSE_INPUT

# --- Функція обробки введення (залишити як є) ---

async def process_expense_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    expense_type = context.user_data.get('expense_type', 'dividends')
    selected_date = context.user_data.get('selected_date', datetime.datetime.now().strftime("%d.%m.%Y")) 

    if expense_type == 'dividends':
        parsed = parse_expense(text)
    else:
        # Для OTHER використовуємо спрощений парсер, оскільки всі деталі вже зібрані
        parsed = parse_expense_simple(text)

    if parsed and 'сума' in parsed:
        try:
            parsed['Дата'] = selected_date 
            add_expense_to_sheet(parsed, context.user_data, expense_type)
            
            # Додаємо у повідомлення деталі, які ми щойно зібрали
            period = context.user_data.get('period', 'N/A')
            location = context.user_data.get('location', 'N/A')
            change = context.user_data.get('change', 'N/A')
            category = context.user_data.get('category', 'N/A')
            subcategory = context.user_data.get('subcategory', 'N/A')
            subsubcategory = context.user_data.get('subsubcategory', 'N/A')
            
            msg = f"✅ Додано в **{expense_type.upper()}**!\n"
            msg += f"**Дата**: {selected_date}\n"
            if expense_type == 'other':
                msg += f"**Період**: {period}\n**Локація**: {location}\n**Зміна**: {change}\n"
                msg += f"**Категорія**: {category}\n**Підкатегорія**: {subcategory}\n**Підпідкатегорія**: {subsubcategory}\n"
            msg += f"**Сума**: {parsed['сума']} грн"
            
            await update.message.reply_text(msg, parse_mode='Markdown')
        except Exception as e:
            logging.error(f"❌ Помилка запису в Sheets: {e}")
            await update.message.reply_text(f"❌ Помилка запису. Деталі: {e}")
            await update.message.reply_text("Спробуйте ввести дані ще раз або натисніть Назад.")
            return WAITING_EXPENSE_INPUT 
    else:
        await update.message.reply_text("⚠️ Не розпізнано. Спробуй ще (формат: СУМА ОПИС).")
        return WAITING_EXPENSE_INPUT

    context.user_data.clear()
    await send_main_menu(update, context, text="Операція завершена.")
    return ConversationHandler.END