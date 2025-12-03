# handlers/utils.py (Повний фікс: додано ask_subcategory_menu та ask_subsubcategory_menu)
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import (
    CONFIG_OTHER, CHANGE_ASCII_TO_UKR, SUB_ASCII_TO_UKR, SUBSUB_ASCII_TO_UKR,
    CAT_ASCII_TO_UKR  # Додано для мапінгів категорій, якщо потрібно
)

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

async def handle_back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник для кнопки 'Назад'. Завершує ConversationHandler і повертає головне меню."""
    if update.callback_query:
        await update.callback_query.answer()
        # ✅ КРИТИЧНИЙ ФІКС: Видаляємо inline-меню, щоб воно не залишалося на екрані
        try:
            await update.callback_query.message.delete()
        except Exception as e:
            # Якщо не вдалося видалити, редагуємо повідомлення
            try:
                await update.callback_query.message.edit_text("⬅️ Повернуто до головного меню.")
            except Exception:
                pass
    
    # Очищуємо всі дані користувача
    context.user_data.clear()
    
    # Показуємо головне меню
    await send_main_menu(update, context, text="⬅️ Повернуто до головного меню.")
        
    return ConversationHandler.END

async def _ask_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, config_key: str, prompt: str, callback_prefix: str, mapping_dict=None, is_list=False, filter_key=None):
    """Універсальна функція для відображення inline-меню за конфігом. Підтримує dict/list."""
    keyboard = []
    current_row = []
    if is_list:
        items_list = CONFIG_OTHER.get(config_key, {}).get(filter_key, []) if filter_key else CONFIG_OTHER.get(config_key, [])
        for key in items_list:
            name = mapping_dict.get(key, key) if mapping_dict else key
            current_row.append(InlineKeyboardButton(name, callback_data=f"{callback_prefix}_{key}"))
            if len(current_row) == 2:
                keyboard.append(current_row)
                current_row = []
        if current_row:
            keyboard.append(current_row)
    else:
        items = CONFIG_OTHER.get(config_key, {})
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
    return await _ask_menu(
        update, context, 
        config_key='periods', 
        prompt="🗓️ Оберіть **Період** (Табір/Місяць):", 
        callback_prefix='period'
    )

async def ask_location_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    period_key = context.user_data.get('period_key')
    if not period_key:
        if update.callback_query:
            await update.callback_query.message.edit_text("❌ Помилка: Не вибрано період. Назад.")
            await update.callback_query.answer()
        else:
            await update.message.reply_text("❌ Помилка: Не вибрано період. Назад.")
        return await handle_back_to_main(update, context)
    
    available_locations = CONFIG_OTHER['locations_by_period'].get(period_key, [])
    full_locations = CONFIG_OTHER['locations']
    filtered_items = {k: full_locations[k] for k in available_locations if k in full_locations}
    
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
    period_key = context.user_data.get('period_key')
    location_key = context.user_data.get('location_key')
    if not period_key or not location_key:
        if update.callback_query:
            await update.callback_query.message.edit_text("❌ Помилка: Не вибрано період або локацію. Назад.")
            await update.callback_query.answer()
        else:
            await update.message.reply_text("❌ Помилка: Не вибрано період або локацію. Назад.")
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
    """Показує меню для вибору Категорії (динамічне на основі локації)."""
    location_key = context.user_data.get('location_key')
    if not location_key:
        if update.callback_query:
            await update.callback_query.message.edit_text("❌ Помилка: Не вибрано локацію. Назад.")
            await update.callback_query.answer()
        else:
            await update.message.reply_text("❌ Помилка: Не вибрано локацію. Назад.")
        return await handle_back_to_main(update, context)
    
    # Динамічне: categories_by_location[location_key] = {cat_key: cat_name}
    categories_dict = CONFIG_OTHER.get('categories_by_location', {}).get(location_key, {})
    
    keyboard = []
    current_row = []
    for cat_key, cat_name in categories_dict.items():
        # Якщо cat_name є list (nested), розгорни: але припустимо dict {key: name}
        current_row.append(InlineKeyboardButton(cat_name, callback_data=f"category_{cat_key}"))
        if len(current_row) == 2:
            keyboard.append(current_row)
            current_row = []
    if current_row:
        keyboard.append(current_row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    prompt = f"📑 Оберіть **Категорію** (для локації '{context.user_data.get('location', 'N/A')}'):"
    
    if update.callback_query:
        await update.callback_query.message.edit_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')
        await update.callback_query.answer()
    elif update.message:
        await update.message.reply_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')

async def ask_subcategory_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує меню для вибору Підкатегорії (динамічне на основі категорії)."""
    category_key = context.user_data.get('category_key')
    if not category_key:
        if update.callback_query:
            await update.callback_query.message.edit_text("❌ Помилка: Не вибрано категорію. Назад.")
            await update.callback_query.answer()
        else:
            await update.message.reply_text("❌ Помилка: Не вибрано категорію. Назад.")
        return await handle_back_to_main(update, context)
    
    # Динамічне: subcategories_by_category[category_key] = {sub_key: name} або list ключів
    subcats_raw = CONFIG_OTHER.get('subcategories_by_category', {}).get(category_key, {})
    if isinstance(subcats_raw, list):
        # Якщо list ключів, мапимо з SUB_ASCII_TO_UKR
        subcats = {k: SUB_ASCII_TO_UKR.get(k, k) for k in subcats_raw}
    else:
        subcats = subcats_raw  # Припустимо dict {key: name}
    
    keyboard = []
    current_row = []
    for sub_key, sub_name in subcats.items():
        current_row.append(InlineKeyboardButton(sub_name, callback_data=f"subcategory_{sub_key}"))
        if len(current_row) == 2:
            keyboard.append(current_row)
            current_row = []
    if current_row:
        keyboard.append(current_row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    prompt = f"📂 Оберіть **Підкатегорію** (для категорії '{context.user_data.get('category', 'N/A')}'):"
    
    if update.callback_query:
        await update.callback_query.message.edit_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')
        await update.callback_query.answer()
    elif update.message:
        await update.message.reply_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')

async def ask_subsubcategory_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує меню для вибору Підпідкатегорії (динамічне на основі підкатегорії)."""
    subcategory_key = context.user_data.get('subcategory_key')
    if not subcategory_key:
        if update.callback_query:
            await update.callback_query.message.edit_text("❌ Помилка: Не вибрано підкатегорію. Назад.")
            await update.callback_query.answer()
        else:
            await update.message.reply_text("❌ Помилка: Не вибрано підкатегорію. Назад.")
        return await handle_back_to_main(update, context)
    
    # Динамічне: subsubcategories_by_subcategory[subcategory_key] = list ключів або dict
    subsubs_raw = CONFIG_OTHER.get('subsubcategories_by_subcategory', {}).get(subcategory_key, [])
    if isinstance(subsubs_raw, dict):
        subsubs = subsubs_raw
    else:
        # Якщо list ключів, мапимо з SUBSUB_ASCII_TO_UKR
        subsubs = {k: SUBSUB_ASCII_TO_UKR.get(k, k) for k in subsubs_raw}
    
    keyboard = []
    current_row = []
    for subsub_key, subsub_name in subsubs.items():
        current_row.append(InlineKeyboardButton(subsub_name, callback_data=f"subsubcategory_{subsub_key}"))
        if len(current_row) == 2:
            keyboard.append(current_row)
            current_row = []
    if current_row:
        keyboard.append(current_row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    prompt = f"📂 Оберіть **Підпідкатегорію** (для підкатегорії '{context.user_data.get('subcategory', 'N/A')}'):"
    
    if update.callback_query:
        await update.callback_query.message.edit_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')
        await update.callback_query.answer()
    elif update.message:
        await update.message.reply_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')