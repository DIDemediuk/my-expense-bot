# handlers/utils.py (ПОВНИЙ РОБОЧИЙ КОД)
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup # <-- ВАЖЛИВО!
from telegram.ext import ContextTypes
# ⚠️ Потрібен імпорт CONFIG_OTHER для роботи нових меню
from config import CONFIG_OTHER 

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
            # Спроба відредагувати попереднє повідомлення та додати клавіатуру
            await query.message.edit_text(text)
            await query.message.reply_text(text, reply_markup=reply_markup)
        except Exception:
            # Якщо повідомлення вже не можна редагувати — просто надсилаємо нове
            await query.message.reply_text(text, reply_markup=reply_markup)

    else:
        # Fallback для інших типів Update
        pass 

# === ФУНКЦІЇ ДЛЯ ПОКРОКОВОГО МЕНЮ ВИТРАТ ===

async def _ask_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, config_key: str, prompt: str, callback_prefix: str):
    """Універсальна функція для відображення inline-меню за конфігом."""
    items = CONFIG_OTHER.get(config_key, {})
    keyboard = []
    
    current_row = []
    for key, name in items.items():
        # Формат callback_data: {callback_prefix}_{key}
        current_row.append(InlineKeyboardButton(name, callback_data=f"{callback_prefix}_{key}"))
        if len(current_row) == 2:
            keyboard.append(current_row)
            current_row = []
    
    if current_row:
        keyboard.append(current_row)
        
    # Кнопка Назад
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Визначаємо, яке повідомлення редагувати/надсилати
    if update.callback_query:
        await update.callback_query.message.edit_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')
        await update.callback_query.answer()
    elif update.message:
        await update.message.reply_text(prompt, reply_markup=reply_markup, parse_mode='Markdown')


async def ask_period_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує меню для вибору періоду витрати (Табір/Місяць)."""
    return await _ask_menu(
        update, context, 
        config_key='periods', 
        prompt="🗓️ Оберіть **Період** (Табір/Місяць):", 
        callback_prefix='period'
    )

async def ask_location_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує меню для вибору локації."""
    return await _ask_menu(
        update, context, 
        config_key='locations', 
        prompt="📍 Оберіть **Локацію**:", 
        callback_prefix='location'
    )

async def ask_change_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує меню для вибору Зміни/Особи."""
    return await _ask_menu(
        update, context, 
        config_key='changes', 
        prompt="👤 Оберіть **Зміну** (Особу):", 
        callback_prefix='change'
    )
    
async def ask_category_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує меню для вибору Категорії."""
    return await _ask_menu(
        update, context, 
        config_key='categories', 
        prompt="📑 Оберіть **Категорію**:", 
        callback_prefix='category'
    )