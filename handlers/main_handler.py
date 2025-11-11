# handlers/main_handler.py (ПОВНИЙ ВИПРАВЛЕНИЙ КОД)
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    WAITING_REPORT_OWNER, WAITING_REPORT_FOP,
    WAITING_EXPENSE_TYPE, WAITING_EXPENSE_INPUT,
    WAITING_PERIOD, WAITING_LOCATION, WAITING_CHANGE,
    WAITING_CATEGORY, WAITING_SUBCATEGORY, WAITING_SUBSUBCATEGORY,
    CONFIG_OTHER, CAT_ASCII_TO_UKR, SUB_ASCII_TO_UKR, SUBSUB_ASCII_TO_UKR,
    CHANGE_ASCII_TO_UKR, CAT_UKR_TO_ASCII, SUB_UKR_TO_ASCII, SUBSUB_UKR_TO_ASCII,
    WAITING_EXPENSE_DATE, WAITING_MANUAL_DATE
)

# ✅ ВИПРАВЛЕНО: Відновлюємо імпорт ask_expense_date
from handlers.expense_handler import ask_expense_date 
# ✅ Тепер handle_back_to_main імпортується з utils (фікс циклічного імпорту)
from handlers.utils import send_main_menu, handle_back_to_main 
from handlers.report_handler import send_reports_menu, show_period_selection, handle_period_report
from reports import generate_daily_report, generate_camp_summary


# === Головне меню ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок роботи / стартове меню"""
    await send_main_menu(update, context, "👋 Привіт! Обери дію нижче:")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повідомлення поза контекстом кнопок"""
    # ... (Ваша існуюча логіка обробки повідомлень, що не є командами/контекстом) ...
    text = update.message.text
    if text == "➕ Додати витрату":
        # Це має обробляти ConversationHandler, але на всяк випадок перенаправимо на старт
        return await ask_expense_date(update, context)
    elif text == "📊 Звіти":
        # Обробка кнопки "Звіти" з головного меню
        await send_reports_menu(update)
        return ConversationHandler.END
    
    # ... (інша логіка) ...


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник усіх callback-кнопок, що не належать ConversationHandler'ам"""
    query = update.callback_query
    await query.answer()
    data = query.data

    # --- Додати витрату ---
    if data == "add_expense":
        # ✅ ТЕПЕР ask_expense_date ВИЗНАЧЕНО
        return await ask_expense_date(update, context)

    # --- Звіти: Головне меню звітів ---
    elif data == "reports_menu":
        await send_reports_menu(update)
        return ConversationHandler.END
    
    # --- Звіт по періоду ---
    elif data == "report_period":
        return await show_period_selection(update, context)
    
    elif data.startswith("period_report_"):
        return await handle_period_report(update, context)
    
    # --- Назад до меню звітів ---
    elif data == "back_to_reports":
        await send_reports_menu(update)
        return ConversationHandler.END

    # --- Щоденний звіт ---
    elif data == "daily_report":
        report_text, parse_mode = generate_daily_report()
        await query.message.edit_text(report_text, parse_mode=parse_mode)
        await send_main_menu(update, context)
        return ConversationHandler.END

    # --- Звіти по табору (Camp Summary) ---
    elif data == "camp_summary_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("☀️ Літо 2025", callback_data="camp_summary_lito_2025"),
             InlineKeyboardButton("🍂 Осінь 2025", callback_data="camp_summary_osin_2025")],
            [InlineKeyboardButton("❄️ Зима 2026", callback_data="camp_summary_zima_2026")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="reports_menu")]
        ])
        await query.message.edit_text("Оберіть табір для звіту:", reply_markup=keyboard)
        return ConversationHandler.END

    elif data.startswith("camp_summary_"):
        key = data.split("_", 2)[-1]
        camp_name = CONFIG_OTHER['periods'].get(key, key)
        report_text, parse_mode = generate_camp_summary(camp_name)
        await query.message.edit_text(report_text, parse_mode=parse_mode)
        await send_main_menu(update, context)
        return ConversationHandler.END

    # --- Назад у головне меню ---
    elif data in ("back_main", "back"):
        # ✅ handle_back_to_main тепер з utils.py
        return await handle_back_to_main(update, context)
        
    return ConversationHandler.END # За замовчуваннямй