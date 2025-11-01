from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import logging
from config import (
    WAITING_REPORT_PERIOD, WAITING_REPORT_OWNER, WAITING_REPORT_FOP, WAITING_EXPENSE_TYPE, WAITING_EXPENSE_INPUT,
    WAITING_PERIOD, WAITING_LOCATION, WAITING_CHANGE, WAITING_CATEGORY, WAITING_SUBCATEGORY, WAITING_SUBSUBCATEGORY,
    CONFIG_OTHER, CAT_ASCII_TO_UKR, SUB_ASCII_TO_UKR, SUBSUB_ASCII_TO_UKR, CHANGE_ASCII_TO_UKR,
    CAT_UKR_TO_ASCII, SUB_UKR_TO_ASCII, SUBSUB_UKR_TO_ASCII, WAITING_EXPENSE_DATE, WAITING_MANUAL_DATE
)
from handlers.expense_handler import ask_expense_date, show_expense_type_selection # Можливо, потрібно буде додати show_expense_type_selection
from reports import generate_daily_report, generate_camp_summary

# --- Головне меню та загальні функції ---

async def handle_back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очищає дані користувача та повертає в головне меню, завершуючи розмову."""
    context.user_data.clear()
    await send_main_menu(update, context)
    return ConversationHandler.END

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text="🔹 Оберіть дію нижче:"):
    """Надсилає або редагує повідомлення з головним меню."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Додати витрату", callback_data="add_expense"),
         InlineKeyboardButton("📊 Звіти", callback_data="reports_menu")]
    ])
    
    # Використовуємо .reply_text для нових повідомлень (наприклад, /start)
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)
    # Використовуємо .edit_text для оновлення повідомлення після callback
    elif update.callback_query:
        try:
            await update.callback_query.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            # Обробка випадку, коли повідомлення не можна відредагувати (наприклад, дуже старе)
            logging.warning(f"Failed to edit message for main menu: {e}")
            await update.callback_query.message.reply_text(text, reply_markup=keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_main_menu(update, context, "👋 Привіт! Тут ти можеш додати витрати до системи")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ Використовуй кнопки. /start")
    await send_main_menu(update, context)


# --- Callback handler з використанням edit_text ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if 'nav_stack' not in context.user_data:
        context.user_data['nav_stack'] = []
        
    # Використовуємо message.edit_text замість reply_text у більшості випадків.
    
    # --- Додати витрату ---
    if query.data == "add_expense":
        context.user_data['nav_stack'] = []
        context.user_data.pop('is_transfer', None)
        user_id = query.from_user.id
        try:
            from handlers.simplified_expense import USER_ROLES, simplified_expense_flow
            if user_id in USER_ROLES:
                # Цей потік зазвичай не редагує повідомлення
                return await simplified_expense_flow(update, context, user_id)
        except ImportError:
            pass
        # Перехід до ask_expense_date
        return await ask_expense_date(update, context)

    # --- Вибір дати ---
    elif query.data.startswith("expense_date_done_"):
        selected_date = query.data.replace("expense_date_done_", "")
        context.user_data["selected_date"] = selected_date
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Dividends", callback_data="expense_type_dividends"),
             InlineKeyboardButton("📈 Other Expenses", callback_data="expense_type_other")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
        ])
        # ✅ Використовуємо edit_text для відображення наступного кроку
        await query.message.edit_text(
            f"📅 Обрана дата: {selected_date}\n\nОбери тип:", 
            reply_markup=keyboard
        )
        return WAITING_EXPENSE_TYPE

    # --- Вибір типу витрати ---
    elif query.data.startswith("expense_type_"):
        expense_type = query.data.split("_")[-1]
        context.user_data['expense_type'] = expense_type
        if expense_type == 'dividends':
            prompt = "Введи: ФОП радул Ваня Мантра 3600 ЗП"
            # ✅ Використовуємо edit_text
            await query.message.edit_text(f"Тип: {expense_type}\n{prompt}")
            return WAITING_EXPENSE_INPUT
        else:
            context.user_data['nav_stack'].append('type')
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("☀️ Літо 2025", callback_data="per_lito_2025"),
                 InlineKeyboardButton("🍂 Осінь 2025", callback_data="per_osin_2025")],
                [InlineKeyboardButton("❄️ Зима 2026", callback_data="per_zima_2026")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
            ])
            # ✅ Використовуємо edit_text
            await query.message.edit_text("Обери Період:", reply_markup=keyboard)
            return WAITING_PERIOD

    # --- Вибір періоду ---
    elif query.data.startswith("per_"):
        per_key = query.data.split("_", 1)[-1]
        context.user_data['period'] = CONFIG_OTHER['periods'][per_key]
        context.user_data['nav_stack'].append('period')
        relevant_locs = CONFIG_OTHER.get('locations_by_period', {}).get(per_key, ['all'])
        keyboard_rows = [[InlineKeyboardButton(CONFIG_OTHER['locations'][loc_key], callback_data=f"loc_{loc_key}")]
                         for loc_key in relevant_locs]
        keyboard_rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
        
        # ✅ Використовуємо edit_text
        await query.message.edit_text(
            f"Період: {context.user_data['period']}\nОбери Локацію (релевантні для періоду):",
            reply_markup=InlineKeyboardMarkup(keyboard_rows)
        )
        return WAITING_LOCATION

    # --- Вибір локації ---
    elif query.data.startswith("loc_"):
        loc_key = query.data.split("_", 1)[-1]
        context.user_data['location'] = CONFIG_OTHER['locations'][loc_key]
        context.user_data['nav_stack'].append('location')

        # --- Логіка для Transfer ---
        if loc_key == 'Transfer':
            context.user_data['is_transfer'] = True
            context.user_data['change'] = 'Трансфер'
            transfer_categories = list(CONFIG_OTHER['categories_by_location']['Transfer'].keys())
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(cat, callback_data=f"cat_{CAT_UKR_TO_ASCII.get(cat, cat.lower().replace(' ', '_'))}")]
                for cat in transfer_categories
            ] + [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]])
            # ✅ Використовуємо edit_text
            await query.message.edit_text(f"Локація: {context.user_data['location']}\nОбери Категорію:", reply_markup=keyboard)
            context.user_data['nav_stack'].append('category')
            return WAITING_CATEGORY

        # --- Звичайна локація ---
        per_key = next((k for k, v in CONFIG_OTHER['periods'].items() if v == context.user_data.get('period')), None)
        changes_config = CONFIG_OTHER.get('changes_by_location_period', {}).get(per_key, {})
        relevant_changes = changes_config.get(loc_key, list(CHANGE_ASCII_TO_UKR.keys()))
        keyboard_rows = [[InlineKeyboardButton(CHANGE_ASCII_TO_UKR[suffix], callback_data=f"change_{suffix}")]
                         for suffix in relevant_changes]
        keyboard_rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
        # ✅ Використовуємо edit_text
        await query.message.edit_text(
            f"Локація: {context.user_data['location']}\nОбери Зміну (релевантні для локації):",
            reply_markup=InlineKeyboardMarkup(keyboard_rows)
        )
        return WAITING_CHANGE

    # --- Вибір зміни ---
    elif query.data.startswith("change_"):
        suffix = query.data.split("_", 1)[-1]
        change = CHANGE_ASCII_TO_UKR[suffix]
        context.user_data['change'] = change
        context.user_data['nav_stack'].append('change')
        categories = CONFIG_OTHER['categories_by_change'].get(change.lower(), ['Маркетинг'])
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(cat, callback_data=f"cat_{CAT_UKR_TO_ASCII.get(cat, cat.lower().replace(' ', '_'))}")]
            for cat in categories
        ] + [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]])
        # ✅ Використовуємо edit_text
        await query.message.edit_text(f"Зміна: {change}\nОбери Категорію:", reply_markup=keyboard)
        return WAITING_CATEGORY

    # --- Вибір категорії ---
    elif query.data.startswith("cat_"):
        ascii_cat = query.data.split("_", 1)[-1]
        cat = CAT_ASCII_TO_UKR.get(ascii_cat, ascii_cat.replace('_', ' ').title())
        context.user_data['category'] = cat
        context.user_data['nav_stack'].append('category')
        cat_lower = cat.lower()
        subcats = CONFIG_OTHER['subcategories_by_category'].get(cat_lower, [])
        if context.user_data.get('is_transfer'):
            subcats = CONFIG_OTHER['categories_by_location']['Transfer'].get(cat, [])
        if not subcats:
            context.user_data['subcategory'] = ''
            # ✅ Використовуємо edit_text
            await query.message.edit_text(
                f"Категорія: {cat}\n"
                f"Зміни: {CONFIG_OTHER['changes_by_subcategory'].get(cat, 'Стандартні')}\n"
                "Введи рахунок/суму/коментар: ФОП 2 20000 реклама"
            )
            return WAITING_EXPENSE_INPUT
        else:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(sub, callback_data=f"sub_{SUB_UKR_TO_ASCII.get(sub, sub.lower().replace(' ', '_'))}")]
                for sub in subcats
            ] + [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]])
            # ✅ Використовуємо edit_text
            await query.message.edit_text(f"Категорія: {cat}\nОбери Підкатегорію:", reply_markup=keyboard)
            return WAITING_SUBCATEGORY

    # --- Вибір підкатегорії ---
    elif query.data.startswith("sub_"):
        ascii_sub = query.data.split("_", 1)[-1]
        sub = SUB_ASCII_TO_UKR.get(ascii_sub, ascii_sub.replace('_', ' ').title())
        context.user_data['subcategory'] = sub
        context.user_data['nav_stack'].append('subcategory')
        sub_lower = sub.lower()
        subsubs = CONFIG_OTHER.get('subsubcategories_by_subcategory', {}).get(sub_lower, [])
        if subsubs:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(s, callback_data=f"subsub_{SUBSUB_UKR_TO_ASCII.get(s, s.lower().replace(' ', '_'))}")]
                for s in subsubs
            ] + [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]])
            # ✅ Використовуємо edit_text
            await query.message.edit_text(f"Підкатегорія: {sub}\nОбери суб-підкатегорію:", reply_markup=keyboard)
            context.user_data['nav_stack'].append('subsubcategory')
            return WAITING_SUBSUBCATEGORY
        else:
            context.user_data['subsubcategory'] = ''
            # ✅ Використовуємо edit_text
            await query.message.edit_text(
                f"Підкатегорія: {sub}\n"
                f"Зміни: {CONFIG_OTHER['changes_by_subcategory'].get(sub, 'Стандартні')}\n"
                "Введи рахунок/суму/коментар: ФОП 2 20000 реклама"
            )
            return WAITING_EXPENSE_INPUT

    # --- Вибір суб-підкатегорії ---
    elif query.data.startswith("subsub_"):
        ascii_subsub = query.data.split("_", 2)[-1]
        subsub = SUBSUB_UKR_TO_ASCII.get(ascii_subsub, ascii_subsub.replace('_', ' ').title())
        context.user_data['subsubcategory'] = subsub
        context.user_data['nav_stack'].append('subsubcategory')
        sub = context.user_data.get('subcategory', '')
        # ✅ Використовуємо edit_text
        await query.message.edit_text(
            f"Суб-підкатегорія: {subsub} (під {sub})\n"
            f"Зміни: {CONFIG_OTHER['changes_by_subcategory'].get(sub, 'Стандартні')}\n"
            "Введи рахунок/суму/коментар: ФОП 2 20000 реклама"
        )
        return WAITING_EXPENSE_INPUT

    # --- Назад (один крок) ---
    elif query.data == "back":
        if not context.user_data['nav_stack']:
            # Якщо стек пустий, повертаємось у головне меню
            return await handle_back_main(update, context)
        
        # Наразі логіка "назад" просто завершує розмову і повертає в головне меню.
        # Для повноцінного переходу на попередній крок потрібен складніший рефакторинг.
        await send_main_menu(update, context, "Повернення в головне меню.")
        return ConversationHandler.END

    # --- Головне меню ---
    elif query.data == "back_main":
        return await handle_back_main(update, context)

    # --- Звіти ---
    elif query.data == "reports_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Dividends звіти", callback_data="reports_div"),
             InlineKeyboardButton("📊 Other звіти", callback_data="reports_other")],
            [InlineKeyboardButton("📅 Звіт за день", callback_data="daily_report"),
             InlineKeyboardButton("🏕️ Звіт по табору", callback_data="camp_summary_menu")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
        ])
        # ✅ Використовуємо edit_text
        await query.message.edit_text("Обери аркуш для звіту:", reply_markup=keyboard)

    # --- Звіт по табору ---
    elif query.data == "camp_summary_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("☀️ Літо 2025", callback_data="camp_summary_lito_2025"),
             InlineKeyboardButton("🍂 Осінь 2025", callback_data="camp_summary_osin_2025")],
            [InlineKeyboardButton("❄️ Зима 2026", callback_data="camp_summary_zima_2026")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="reports_menu")]
        ])
        # ✅ Використовуємо edit_text
        await query.message.edit_text("Оберіть табір для звіту:", reply_markup=keyboard)

    elif query.data.startswith("camp_summary_"):
        key = query.data.split("_", 2)[-1]
        camp_name = CONFIG_OTHER['periods'].get(key, key)
        report_text, parse_mode = generate_camp_summary(camp_name)
        # ✅ Редагуємо повідомлення звітом
        await query.message.edit_text(report_text, parse_mode=parse_mode)
        await send_main_menu(update, context)

    # --- Звіт за день ---
    elif query.data == "daily_report":
        report_text, parse_mode = generate_daily_report()
        # ✅ Редагуємо повідомлення звітом
        await query.message.edit_text(report_text, parse_mode=parse_mode)
        await send_main_menu(update, context)

    # --- Звіти Dividends / Other ---
    elif query.data == "reports_div":
        context.user_data['report_type'] = 'dividends'
        # ✅ Використовуємо edit_text
        await query.message.edit_text("Введи ім’я власника для звіту:")
        return WAITING_REPORT_OWNER
    elif query.data == "reports_other":
            context.user_data['report_type'] = 'other'
            # ✅ Використовуємо edit_text
            await query.message.edit_text("Введи ФОП або ключове слово для звіту:")
            return WAITING_REPORT_FOP  # <-- Виправлено на WAITING_REPORT_FOP