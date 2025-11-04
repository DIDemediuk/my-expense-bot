# handlers/utils.py (Виправлений код з динамічними меню для changes та locations)
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler  # <-- Потрібен для handle_back_to_main
from config import CONFIG_OTHER, CHANGE_ASCII_TO_UKR  # Додано імпорт мапінгу для changes
from handlers.utils import send_main_menu  # Якщо потрібно, але уникаємо циклу

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text="🔹 Оберіть дію нижче:"):
    """Відображає головне меню користувачу."""
    keyboard = [
        [KeyboardButton("➕ Додати витрату")],
        [KeyboardButton("📊 Звіти")],
        [KeyboardButton("🔙 Закрити меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    if update.message:
        user_text = update.message.text if update.message.text else ""
        if user_text == "🔙 Закрити меню":
            await update.message.reply_text("Меню закрито 👌", reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)

    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.message.edit_text(text)
            await query.message.reply_text(text, reply_markup=reply_markup)
        except Exception:
            await query.message.reply_text(text, reply_markup=reply_markup)
    else:
        pass 

# ✅ ФУНКЦІЯ ДЛЯ РОЗІРВАННЯ ЦИКЛІЧНОГО ІМПОРТУ
async def handle_back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник для кнопки 'Назад'. Завершує ConversationHandler і повертає головне меню."""
    if update.callback_query:
        await update.callback_query.answer()
    
    await send_main_menu(update, context, text="⬅️ Повернуто до головного меню.")
    
    # Очищуємо дані, пов'язані з поточною розмовою
    if context.user_data:
        context.user_data.clear()
        
    return ConversationHandler.END


# === ФУНКЦІЇ ДЛЯ ПОКРОКОВОГО МЕНЮ ВИТРАТ ===

async def _ask_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, config_key: str, prompt: str, callback_prefix: str, mapping_dict=None, is_list=False, filter_key=None):
    """Універсальна функція для відображення inline-меню за конфігом. Підтримує dict/list."""
    if is_list:
        # Для динамічних списків (e.g. changes)
        items_list = CONFIG_OTHER.get(config_key, {}).get(filter_key, []) if filter_key else CONFIG_OTHER.get(config_key, [])
        keyboard = []
        current_row = []
        for key in items_list:
            name = mapping_dict.get(key, key) if mapping_dict else key
            current_row.append(InlineKeyboardButton(name, callback_data=f"{callback_prefix}_{key}"))
            if len(current_row) == 2:
                keyboard.append(current_row)
                current_row = []
        if current_row:
            keyboard.append(current_row)
    else:
        # Для статичних dict (e.g. periods, locations)
        items = CONFIG_OTHER.get(config_key, {})
        keyboard = []
        current_row = []
        for key, name in items.items():
            current_row.append(InlineKeyboardButton(name, callback_data=f"{callback_prefix}_{key}"))
            if len(current_row) == 2:
                keyboard.append(current_row)
                current_row = []
        if current_row:
            keyboard.append(current_row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')
        await update.callback_query.answer()
    elif update.message:
        await update.message.reply_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')

async def ask_period_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує меню для вибору періоду витрати (статичний dict)."""
    return await _ask_menu(
        update, context, 
        config_key='periods', 
        prompt="🗓️ Оберіть **Період** (Табір/Місяць):", 
        callback_prefix='period'
    )

async def ask_location_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує меню для вибору локації (динамічний список на основі періоду)."""
    period_key = context.user_data.get('period_key')
    if not period_key:
        await update.callback_query.message.edit_text("❌ Помилка: Не вибрано період. Назад.")
        return await handle_back_to_main(update, context)
    
    available_locations = CONFIG_OTHER['locations_by_period'].get(period_key, [])
    # Фільтруємо повний список локацій
    full_locations = CONFIG_OTHER['locations']
    filtered_items = {k: full_locations[k] for k in available_locations if k in full_locations}
    
    # Використовуємо _ask_menu з items=filtered_items (як dict)
    keyboard = []
    current_row = []
    for key, name in filtered_items.items():
        current_row.append(InlineKeyboardButton(name, callback_data=f"location_{key}"))
        if len(current_row) == 2:
            keyboard.append(current_row)
            current_row = []
    if current_row:
        keyboard.append(current_row)
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    prompt = "📍 Оберіть **Локацію** (доступні для обраного періоду):"
    
    if update.callback_query:
        await update.callback_query.message.edit_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')
        await update.callback_query.answer()
    elif update.message:
        await update.message.reply_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')

async def ask_change_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує меню для вибору Зміни/Особи (динамічний список на основі періоду + локації)."""
    period_key = context.user_data.get('period_key')
    location_key = context.user_data.get('location_key')
    if not period_key or not location_key:
        await update.callback_query.message.edit_text("❌ Помилка: Не вибрано період або локацію. Назад.")
        return await handle_back_to_main(update, context)
    
    changes_list = CONFIG_OTHER['changes_by_location_period'].get(period_key, {}).get(location_key, [])
    
    keyboard = []
    current_row = []
    for change_key in changes_list:
        name = CHANGE_ASCII_TO_UKR.get(change_key, change_key)
        current_row.append(InlineKeyboardButton(name, callback_data=f"change_{change_key}"))
        if len(current_row) == 2:
            keyboard.append(current_row)
            current_row = []
    if current_row:
        keyboard.append(current_row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    prompt = "👤 Оберіть **Зміну** (Особу):"
    
    if update.callback_query:
        await update.callback_query.message.edit_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')
        await update.callback_query.answer()
    elif update.message:
        await update.message.reply_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')

async def ask_category_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує меню для вибору Категорії (динамічний на основі локації, припускаємо dict)."""
    location_key = context.user_data.get('location_key')
    if not location_key:
        await update.callback_query.message.edit_text("❌ Помилка: Не вибрано локацію. Назад.")
        return await handle_back_to_main(update, context)
    
    categories_dict = CONFIG_OTHER['categories_by_location'].get(location_key, {})
    
    keyboard = []
    current_row = []
    for cat_key, cat_name in categories_dict.items():  # Припускаємо {key: name} або nested
        # Якщо nested dict, адаптуй: e.g. for sub_key, sub_name in cat_dict.items()
        current_row.append(InlineKeyboardButton(cat_name, callback_data=f"category_{cat_key}"))
        if len(current_row) == 2:
            keyboard.append(current_row)
            current_row = []
    if current_row:
        keyboard.append(current_row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    prompt = "📑 Оберіть **Категорію** (для обраної локації):"
    
    if update.callback_query:
        await update.callback_query.message.edit_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')
        await update.callback_query.answer()
    elif update.message:
        await update.message.reply_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')