# handlers/expense_handler.py (ВИПРАВЛЕНО)
import datetime
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
# Додано всі необхідні константи станів
from config import (
    WAITING_EXPENSE_DATE, WAITING_MANUAL_DATE, WAITING_EXPENSE_TYPE, WAITING_EXPENSE_INPUT,
    WAITING_PERIOD, WAITING_LOCATION, WAITING_CHANGE, WAITING_CATEGORY,
    WAITING_SUBCATEGORY, WAITING_SUBSUBCATEGORY, CONFIG_OTHER # <--- CONFIG_OTHER теж потрібен
) 
from sheets import add_expense_to_sheet, parse_expense, parse_expense_simple
# ✅ КРИТИЧНЕ ВИПРАВЛЕННЯ: Додано всі функції меню
from handlers.utils import (
    send_main_menu, 
    ask_period_menu,  
    ask_location_menu,
    ask_change_menu,
    ask_category_menu
) 
from handlers.main_handler import handle_back_to_main # Імпорт функції для "Назад"

# --- Функції обробки дати (залишити як є) ---
# ... ask_expense_date, handle_expense_date_selection, handle_manual_date_input ...

# --- Функції обробки типу витрат (КРИТИЧНА ЛОГІКА) ---
async def show_expense_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, selected_date: str):
    # ... (залишити як є) ...
    return WAITING_EXPENSE_TYPE

async def handle_expense_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    expense_type = data.split('_')[-1] # dividends або other

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
        return WAITING_PERIOD # <-- Перехід до очікування вибору Періоду
    
    return ConversationHandler.END

# --- НОВІ ОБРОБНИКИ ДЛЯ ПЕРІОДУ ТА ЛОКАЦІЇ ---
async def handle_period_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    period_key = query.data.split('_', 1)[-1] 
    period_name = CONFIG_OTHER['periods'].get(period_key, period_key)
    context.user_data['period'] = period_name
    
    # Перехід до вибору Локації
    await ask_location_menu(update, context) 
    return WAITING_LOCATION 

async def handle_location_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    location_key = query.data.split('_', 1)[-1] 
    location_name = CONFIG_OTHER['locations'].get(location_key, location_key)
    context.user_data['location'] = location_name
    
    # Перехід до вибору Зміни/Особи
    await ask_change_menu(update, context) 
    return WAITING_CHANGE 

# --- Функція обробки введення (залишити як є) ---
# ... process_expense_input ...

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