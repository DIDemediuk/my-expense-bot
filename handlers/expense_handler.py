import datetime
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
# Додано WAITING_EXPENSE_INPUT для коректного переходу
from config import (
    WAITING_EXPENSE_DATE, WAITING_MANUAL_DATE, WAITING_EXPENSE_TYPE, WAITING_EXPENSE_INPUT,
    WAITING_PERIOD, WAITING_LOCATION, WAITING_CHANGE, WAITING_CATEGORY,
    WAITING_SUBCATEGORY, WAITING_SUBSUBCATEGORY, CONFIG_OTHER # <--- CONFIG_OTHER теж потрібен
)
from sheets import add_expense_to_sheet, parse_expense, parse_expense_simple
from handlers.utils import (
    send_main_menu, 
    ask_period_menu,  
    ask_location_menu,
    ask_change_menu,
    ask_category_menu
) 
from handlers.state_utils import handle_back_to_main # ✅ Виправлений імпорт для 'Назад'


# --- Функції обробки дати ---

async def ask_expense_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Сьогодні", callback_data="date_today")],
        [InlineKeyboardButton("📆 Вчора", callback_data="date_yesterday")],
        [InlineKeyboardButton("✏️ Ввести дату вручну", callback_data="date_manual")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        # Використовуємо edit_text, якщо це callback (наприклад, з головного меню)
        await update.callback_query.message.edit_text("📆 Оберіть дату операції:", reply_markup=reply_markup)
        await update.callback_query.answer()
    elif update.message:
        await update.message.reply_text("📆 Оберіть дату операції:", reply_markup=reply_markup)
    else:
        logging.error("❌ Невідомий тип update в ask_expense_date")
        return ConversationHandler.END

    return WAITING_EXPENSE_DATE


async def handle_expense_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "date_today":
        selected_date = datetime.datetime.now().strftime("%d.%m.%Y")
    elif query.data == "date_yesterday":
        selected_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
    elif query.data == "date_manual":
        # Переконайтеся, що edit_text використовується для callback
        await query.message.edit_text("📝 Введіть дату у форматі ДД.ММ.РРРР (наприклад, 27.10.2025):")
        return WAITING_MANUAL_DATE
    elif query.data == "back_main":
        # Тут handle_back_to_main має бути доступним (імпортованим)
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

# --- Функції обробки типу витрат ---

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

# ✅ ВИПРАВЛЕННЯ: Додано відсутню функцію handle_expense_type_selection
async def handle_expense_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    expense_type = data.split('_')[-1] # dividends або other

    context.user_data['expense_type'] = expense_type
    
    if expense_type == 'dividends':
        # Для дивідендів кроки простіші, тому одразу до введення
        await query.message.edit_text(
            f"✅ Тип: **{expense_type.upper()}**\n\n📝 Введіть деталі дивідендів (сума + джерело + власник, напр. '500 ФОП2 Яна'):",
            parse_mode='Markdown'
        )
        return WAITING_EXPENSE_INPUT
        
    elif expense_type == 'other':
        # ✅ Для OTHER: Починаємо покроковий вибір з Періоду
        await ask_period_menu(update, context) 
        return WAITING_PERIOD # <-- Перехід до очікування вибору Періоду
    
    return ConversationHandler.END  

async def handle_period_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # Витягуємо ASCII-ключ періоду
    period_key = data.split('_', 1)[-1] 
    
    # Зберігаємо вибраний період у user_data
    period_name = CONFIG_OTHER['periods'].get(period_key, period_key)
    context.user_data['period'] = period_name
    
    # ✅ Крок 2: Перехід до вибору Локації
    await ask_location_menu(update, context) 
    
    return WAITING_LOCATION # <-- НОВИЙ СТАН

async def handle_location_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # Витягуємо ASCII-ключ локації
    location_key = data.split('_', 1)[-1] 
    
    # Зберігаємо вибрану локацію
    location_name = CONFIG_OTHER['locations'].get(location_key, location_key)
    context.user_data['location'] = location_name
    
    # ✅ Крок 3: Перехід до вибору Зміни/Особи
    await ask_change_menu(update, context) 
    
    return WAITING_CHANGE # <-- НОВИЙ СТАН

# --- Функція обробки введення ---

async def process_expense_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    expense_type = context.user_data.get('expense_type', 'dividends')
    selected_date = context.user_data.get('selected_date', datetime.datetime.now().strftime("%d.%m.%Y")) # Використовуйте дату

    if expense_type == 'dividends':
        # Припускаємо, що parse_expense повертає dict з ключем 'сума'
        parsed = parse_expense(text)
    else:
        parsed = parse_expense_simple(text)

    if parsed and 'сума' in parsed:
        try:
            # Додаємо обрану дату до даних
            parsed['Дата'] = selected_date 
            add_expense_to_sheet(parsed, context.user_data, expense_type)
            
            subsub = context.user_data.get('subsubcategory', '')
            msg = f"✅ Додано в **{expense_type.upper()}**!\n**Дата**: {selected_date}\n**Сума**: {parsed['сума']} грн"
            if subsub:
                msg += f"\n{subsub}"
            await update.message.reply_text(msg, parse_mode='Markdown')
        except Exception as e:
            logging.error(f"❌ Помилка запису в Sheets: {e}")
            await update.message.reply_text(f"❌ Помилка запису. Деталі: {e}")
            await update.message.reply_text("Спробуйте ввести дані ще раз або натисніть Назад.")
            return WAITING_EXPENSE_INPUT # Залишаємось у стані, якщо помилка запису
    else:
        await update.message.reply_text("⚠️ Не розпізнано. Спробуй ще (формат: СУМА ОПИС).")
        return WAITING_EXPENSE_INPUT # Залишаємось у стані, якщо помилка парсингу

    context.user_data.clear()
    await send_main_menu(update, context, text="Операція завершена.")
    return ConversationHandler.END

# --- Обробник 'Назад' ---
# *Примітка: У вашому коді handle_back_to_main імпортується з іншого місця (або його потрібно імпортувати).*
# Я замінив ваш локальний handle_back_to_main на імпорт з handlers.main_handler.
# Якщо у вас цей обробник визначений у main_handler.py, то все гаразд.