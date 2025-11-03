# handlers/main_handler.py
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

from handlers.expense_handler import ask_expense_date
from handlers.utils import send_main_menu
from reports import generate_daily_report, generate_camp_summary
from handlers.state_utils import handle_back_to_main


# === Головне меню ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок роботи / стартове меню"""
    await send_main_menu(update, context, "👋 Привіт! Обери дію нижче:")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повідомлення поза контекстом кнопок"""
    await update.message.reply_text("⚠️ Використовуй кнопки меню нижче 👇")
    await send_main_menu(update, context)


async def handle_back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повернення у головне меню"""
    context.user_data.clear()
    await send_main_menu(update, context)
    return ConversationHandler.END


# === Основна логіка кнопок ===
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Ініціалізація навігаційного стеку
    context.user_data.setdefault('nav_stack', [])

    # --- Головне меню: додати витрату ---
    if data == "add_expense":
        context.user_data.clear()
        return await ask_expense_date(update, context)

    # --- Головне меню: звіти ---
    elif data == "reports_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Dividends звіти", callback_data="reports_div"),
             InlineKeyboardButton("📊 Other звіти", callback_data="reports_other")],
            [InlineKeyboardButton("📅 Звіт за день", callback_data="daily_report"),
             InlineKeyboardButton("🏕️ Звіт по табору", callback_data="camp_summary_menu")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
        ])
        await query.message.edit_text("Оберіть тип звіту:", reply_markup=keyboard)
        return ConversationHandler.END

    # --- Звіт Dividends ---
    elif data == "reports_div":
        context.user_data['report_type'] = 'dividends'
        await query.message.edit_text("Введи ім’я власника для звіту:")
        return WAITING_REPORT_OWNER

    # --- Звіт Other ---
    elif data == "reports_other":
        context.user_data['report_type'] = 'other'
        await query.message.edit_text("Введи ФОП або ключове слово для звіту:")
        return WAITING_REPORT_FOP

    # --- Звіт за день ---
    elif data == "daily_report":
        report_text, parse_mode = generate_daily_report()
        await query.message.edit_text(report_text, parse_mode=parse_mode)
        await send_main_menu(update, context)
        return ConversationHandler.END

    # --- Звіти по табору ---
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
        return await handle_back_main(update, context)

    # --- Якщо callback невідомий ---
    else:
        logging.warning(f"Невідомий callback: {data}")
        await send_main_menu(update, context, "⚠️ Невідома команда. Повертаюсь у головне меню.")
        return ConversationHandler.END
