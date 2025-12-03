import telebot
from telebot import types
import gspread
from google.oauth2.service_account import Credentials
import re
from datetime import datetime, timedelta
from collections import defaultdict
import os
import matplotlib.pyplot as plt
import io
import seaborn as sns
import pandas as pd
from matplotlib.dates import DateFormatter
import numpy as np
import time
from threading import Thread
import matplotlib 
matplotlib.use('Agg')


# === НАЛАШТУВАННЯ ===
BOT_TOKEN = "8509328290:AAFhXhXVl49RyQhrBKnQpYbDIlFODVi03Xc"
SPREADSHEET_NAME = "Витрати"
CREDENTIALS_FILE = "credentials.json"

# === ВИКЛИКИ (залишаємо, бо окремо від досягнень) ===
CHALLENGES = {
    "no_cafe_week": {
        "title": "🍽️ Тиждень без кафе",
        "description": "Не витрачайте на кафе протягом тижня",
        "reward": 50,
        "duration_days": 7
    },
    "smart_shopper": {
        "title": "🛒 Розумний покупець",
        "description": "Витратьте на продукти на 20% менше, ніж минулого тижня",
        "reward": 30,
        "duration_days": 7
    },
    "savings_boost": {
        "title": "📈 Буст накопичень",
        "description": "Збережіть 30% від доходу цього місяця",
        "reward": 70,
        "duration_days": 30
    }
}

# === КАТЕГОРІЇ ===
CATEGORIES = {
    "Дохід": ["ВестКемп", "Кавомашини Дохід", "Інше"],
    "Розхід": [
        "Їжа", "Одяг", "Садочок", "Комунальні платежі", "Розваги",
        "Кафе", "Дні народження", "Подарунки", "Для дому",
        "Кавомашини", "Машина", "Пальне", "Кредитка", "Підписки", "Іграшки"
    ]
}

SUBCATEGORIES = {
    "Кавомашини": ["Розхідники", "Запчастини", "Інше"],
    "Машина": ["Запчастини", "Ремонт"],
    "Їжа": ["АТБ", "Леся магазин", "Стефайно", "Інше"],
    "Садочок": ["Оплата", "Скидання грошей", "Інше"],
    "Комунальні платежі": ["Газ", "Доставка газу", "Світло"],
    "Для дому": ["Аврора", "Копійочка", "Інше"],
    "Підписки": ["Netflix", "Megogo", "Інше"]
}

# === БЮДЖЕТНІ ЛІМІТИ (тепер з персистентністю) ===
BUDGET_LIMITS = {
    "monthly": {},  # {category: limit_amount}
    "notifications": {}  # {category: percentage_to_notify}
}

# === ГЛОБАЛЬНИЙ СТАН КОРИСТУВАЧІВ (для простоти) ===
user_state = {}  # {user_id: {"step": "...", "type": "...", "category": "...", ...}}

# === КЕШ ДАНИХ ТА BATCH ОПЕРАЦІЇ ===


cache = {
    "last_update": None,
    "data": [],
    "monthly_stats": defaultdict(lambda: {"income": 0, "expense": 0}),
    "category_stats": defaultdict(lambda: defaultdict(float)),
    "cache_lifetime": 300,
    "pending_updates": [],
    "last_batch_update": None,
    "batch_update_interval": 60
}

def update_cache(force=False):
    """Оновлення кешу даних з логуванням"""
    global cache
    current_time = datetime.now()
    
    # Перевіряємо чи потрібно оновлювати кеш
    if force or (cache["last_update"] is None or 
        (current_time - cache["last_update"]).total_seconds() > cache["cache_lifetime"]):
        
        if refresh_sheets_connection():
            try:
                # Отримуємо всі дані
                cache["data"] = sheet.get_all_values()
                cache["last_update"] = current_time
                print(f"✅ Кеш оновлено: {len(cache['data'])} рядків")  # Лог
                
                # Розраховуємо статистику
                calculate_statistics()
                return True
            except Exception as e:
                print(f"❌ Помилка оновлення кешу: {e}")
                return False
        else:
            print("❌ Не вдалося з'єднатися з Sheets для оновлення кешу")
    return True

def calculate_statistics():
    global cache
    cache["monthly_stats"] = defaultdict(lambda: {"income": 0, "expense": 0})
    cache["category_stats"] = defaultdict(lambda: defaultdict(float))
    for row in cache["data"][1:]:
        try:
            date_str = row[0].split()[0]
            date = datetime.strptime(date_str, "%Y-%m-%d")
            month_key = date.strftime("%Y-%m")
            op_type = row[1]
            category = row[2]
            amount = float(str(row[4]).replace('\xa0', '').replace(' ', '').replace(',', '.'))
            if op_type == "Дохід":
                cache["monthly_stats"][month_key]["income"] += amount
            else:
                cache["monthly_stats"][month_key]["expense"] += amount
            cache["category_stats"][month_key][category] += amount
        except (ValueError, IndexError) as e:
            print(f"Помилка обробки рядка: {e}")
            continue

# === Підключення до Google Sheets та Batch операції ===
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

def refresh_sheets_connection():
    """Оновлює з'єднання з Google Sheets з логуванням"""
    global creds, client, sheet, budget_sheet
    try:
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open(SPREADSHEET_NAME).sheet1
        # Створюємо/отримуємо аркуш для бюджету, якщо немає
        try:
            budget_sheet = client.open(SPREADSHEET_NAME).worksheet("Budget")
        except gspread.WorksheetNotFound:
            budget_sheet = sheet.add_worksheet(title="Budget", rows=100, cols=10)
            budget_sheet.append_row(["Категорія", "Ліміт (грн)"])  # Заголовки
            print("📊 Створено аркуш Budget")
        print("✅ З'єднання з Google Sheets успішне!")  # Лог
        load_budget_limits()  # Завантажуємо ліміти при підключенні
        return True
    except Exception as e:
        print(f"❌ Помилка підключення до Google Sheets: {e}")
        return False

def load_budget_limits():
    """Завантажує бюджетні ліміти з аркуша Budget"""
    global BUDGET_LIMITS
    try:
        if budget_sheet.row_count <= 1:
            return  # Порожній аркуш
        rows = budget_sheet.get_all_values()[1:]  # Пропускаємо заголовки
        for row in rows:
            if len(row) >= 2 and row[0] and row[1]:
                category = row[0].strip()
                try:
                    limit = float(row[1].replace(' ', '').replace(',', '.'))
                    BUDGET_LIMITS["monthly"][category] = limit
                except ValueError:
                    print(f"⚠️ Невірний ліміт для {category}: {row[1]}")
        print(f"📊 Завантажено {len(BUDGET_LIMITS['monthly'])} лімітів")
    except Exception as e:
        print(f"❌ Помилка завантаження лімітів: {e}")

def save_budget_limits():
    """Зберігає бюджетні ліміти в аркуш Budget"""
    try:
        # Очищаємо аркуш (залишаємо заголовки)
        budget_sheet.clear()
        budget_sheet.append_row(["Категорія", "Ліміт (грн)"])
        for category, limit in BUDGET_LIMITS["monthly"].items():
            budget_sheet.append_row([category, limit])
        print(f"💾 Збережено {len(BUDGET_LIMITS['monthly'])} лімітів")
    except Exception as e:
        print(f"❌ Помилка збереження лімітів: {e}")

def add_to_batch(row_data):
    """Додає операцію до batch-оновлення"""
    cache["pending_updates"].append(row_data)
    print(f"📝 Додано до batch: {row_data}")  # Лог
    
def process_batch_updates():
    """Обробляє накопичені batch-оновлення (негайно, якщо є)"""
    global cache
    
    if not cache["pending_updates"]:
        return True
        
    if not refresh_sheets_connection():
        print("❌ Не вдалося з'єднатися для batch")
        return False
        
    try:
        if cache["pending_updates"]:
            sheet.append_rows(cache["pending_updates"])
            print(f"✅ Batch збережено: {len(cache['pending_updates'])} рядків")  # Лог
            
            # Оновлюємо кеш даних
            cache["data"].extend(cache["pending_updates"])
            
            # Оновлюємо статистику для нових записів
            for row in cache["pending_updates"]:
                try:
                    date_str = row[0].split()[0]
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                    month_key = date.strftime("%Y-%m")
                    
                    op_type = row[1]
                    category = row[2]
                    amount_str = str(row[4]).replace('\xa0', '').replace(' ', '').replace(',', '.')
                    amount = float(amount_str)  # ✅ тепер правильно    
                    
                    if op_type == "Дохід":
                        cache["monthly_stats"][month_key]["income"] += amount
                    else:
                        cache["monthly_stats"][month_key]["expense"] += amount
                    
                    cache["category_stats"][month_key][category] += amount
                except (ValueError, IndexError) as e:
                    print(f"Помилка обробки рядка при оновленні статистики: {e}")
                    continue
            
            # Очищаємо список pending операцій
            cache["pending_updates"] = []
            cache["last_batch_update"] = datetime.now()
            
        return True
    except Exception as e:
        print(f"❌ Помилка при batch-оновленні: {e}")
        return False

# Початкове підключення
creds = None
client = None
sheet = None
budget_sheet = None  # Додано
refresh_sheets_connection()

# Додаємо заголовки, якщо потрібно
try:
    if not sheet.get_all_values():
        sheet.append_row(["Дата", "Тип", "Категорія", "Підкатегорія", "Сума", "Опис"])
        print("📝 Заголовки додано до таблиці")
except:
    pass

bot = telebot.TeleBot(BOT_TOKEN)

def set_user_data(user_id, key, value):
    """Store arbitrary user-specific data in user_state."""
    user_state[user_id] = user_state.get(user_id, {})
    user_state[user_id][key] = value

def set_user_step(user_id, step):
    user_state[user_id] = user_state.get(user_id, {})
    user_state[user_id]["step"] = step

def get_user_data(user_id, key, default=None):
    """Retrieve stored user-specific data."""
    return user_state.get(user_id, {}).get(key, default)

def go_back(user_id):
    """Move the user's step one level back and return the new step.
    If there is no previous step, returns 'start'."""
    current = user_state.get(user_id, {}).get("step")
    prev = "start"
    if current == "choose_date":
        prev = "choose_type"
        set_user_step(user_id, prev)
    elif current == "enter_custom_date":
        prev = "choose_date"
        set_user_step(user_id, prev)
    elif current == "choose_category":
        prev = "choose_date"
        set_user_step(user_id, prev)
    elif current == "choose_subcategory":
        prev = "choose_category"
        set_user_step(user_id, prev)
    elif current == "enter_amount":
        # If a subcategory exists, go back to choosing subcategory, otherwise to category
        if user_state.get(user_id, {}).get("subcategory"):
            prev = "choose_subcategory"
        else:
            prev = "choose_category"
        set_user_step(user_id, prev)
    else:
        # default fallback: go to the main start/menu
        set_user_step(user_id, "choose_type")
        prev = "start"
    return prev

# === START ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("💰 Дохід"),
        types.KeyboardButton("💸 Розхід"),
        types.KeyboardButton("📊 Звіт"),
        types.KeyboardButton("📈 Графіки"),
        types.KeyboardButton("💼 Бюджет"),
        types.KeyboardButton("🗑️ Видалити останнє"),
        types.KeyboardButton("🏆 Виклики")  # Змінено з "🏆 Досягнення" на "🏆 Виклики"
    )
    bot.send_message(message.chat.id, "Привіт! Обери тип операції:", reply_markup=markup)
    set_user_step(message.chat.id, "choose_type")

# === ВИКЛИКИ: показ (адаптовано, без досягнень) ===
@bot.message_handler(func=lambda m: m.text == "🏆 Виклики")  # Змінено handler
def show_challenges(message):  # Перейменовано з show_achievements
    user_id = message.chat.id
    challenges = get_user_challenges(user_id)
    
    # Підраховуємо загальні бали від завершених викликів (адаптовано)
    completed_challenges = [c for c in challenges.values() if c['completed']]
    total_points = sum(CHALLENGES[c_id]['reward'] for c_id, c in challenges.items() if c['completed'])  # Адаптовано для викликів
    
    # Формуємо повідомлення (тільки про виклики)
    message_text = f"🏆 *Ваші виклики*\nЗагальний рахунок: {total_points} балів\n\n"
    
    # Додаємо інформацію про активні виклики
    if challenges:
        message_text += "*Активні виклики:*\n"
        for challenge_id, challenge_data in challenges.items():
            if not challenge_data['completed']:
                challenge = CHALLENGES[challenge_id]
                days_left = (challenge_data['end_date'] - datetime.now()).days
                message_text += f"🎯 {challenge['title']}\n"
                message_text += f"_{challenge['description']}_\n"
                message_text += f"Залишилось днів: {days_left}\n"
    else:
        message_text += "_У вас поки немає активних викликів_\n"
    
    # Додаємо доступні виклики
    available_challenges = [c for c in CHALLENGES.keys() if c not in challenges]
    if available_challenges:
        message_text += "\n*Доступні виклики:*\n"
        for challenge_id in available_challenges:
            challenge = CHALLENGES[challenge_id]
            message_text += f"🎯 {challenge['title']}\n"
            message_text += f"_{challenge['description']}_\n"
            message_text += f"Нагорода: {challenge['reward']} балів\n"
    
    # Розбиваємо повідомлення на частини, якщо воно завелике
    for chunk in split_message(message_text):
        bot.send_message(message.chat.id, chunk, parse_mode="Markdown")
    send_welcome(message)  # Додано: повернення до меню після показу

# === ОБРОБКА ВИБОРУ ТИПУ ===
@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "choose_type")
def choose_type(message):
    # Якщо користувач натиснув кнопку "Звіт" у головному меню
    if message.text and "Звіт" in message.text:
        try:
            show_report_menu(message)
        except Exception as e:
            print(f"Помилка при відкритті меню звіту з choose_type: {e}")
            bot.send_message(message.chat.id, "❌ Не вдалося відкрити меню звіту. Спробуй ще раз.")
        return
    
    # Якщо користувач натиснув кнопку видалення
    if message.text and "Видалити" in message.text:
        try:
            delete_last_record(message)
        except Exception as e:
            print(f"Помилка при видаленні запису з choose_type: {e}")
            bot.send_message(message.chat.id, "❌ Не вдалося видалити запис. Спробуй ще раз.")
        return

    # ФІКС: Додаємо обробку для інших кнопок меню
    if message.text == "📈 Графіки":
        show_charts_menu(message)
        return
    if message.text == "💼 Бюджет":
        show_budget_menu(message)
        return
    if message.text == "🏆 Виклики":
        show_challenges(message)
        return

    if message.text == "↩️ Назад":
        send_welcome(message)
        return

    if "Дохід" in message.text:
        op_type = "Дохід"
    elif "Розхід" in message.text:
        op_type = "Розхід"
    else:
        bot.send_message(message.chat.id, "Обери один із варіантів.")
        return

    set_user_data(message.chat.id, "type", op_type)
    set_user_step(message.chat.id, "choose_date")  # ← новий крок

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Сьогодні", "Вчора", "Ввести дату")
    markup.add("↩️ Назад")
    bot.send_message(
        message.chat.id,
        "Вибери дату операції:",
        reply_markup=markup
    )

# === ЗВІТ: ПОЧАТОК ===
@bot.message_handler(func=lambda m: m.text == "📊 Звіт")
def force_show_report_menu(message):
    show_report_menu(message)

def show_report_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Сьогодні", "Цей тиждень", "Цей місяць")
    markup.add("↩️ Назад")
    bot.send_message(message.chat.id, "Обери період звіту:", reply_markup=markup)
    set_user_step(message.chat.id, "choose_report_period")

def get_user_step(user_id):
    return user_state.get(user_id, {}).get("step")

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "choose_report_period")
def handle_report_period(message):
    if message.text == "↩️ Назад":
        send_welcome(message)
        return

    if message.text in ["Сьогодні", "Цей тиждень", "Цей місяць"]:
        try:
            report_text = generate_report(message.text)
            if not report_text or "немає" in report_text.lower():
                bot.send_message(message.chat.id, "📭 За цей період записів немає.")
            else:
                for chunk in split_message(report_text):
                    bot.send_message(message.chat.id, chunk, parse_mode="Markdown")
            send_welcome(message)  # Залишаємо тільки тут (після успішного звіту)
        except Exception as e:
            print(f"Помилка: {e}")
            bot.send_message(message.chat.id, "❌ Помилка при генерації звіту.")
            send_welcome(message)
    else:
        bot.send_message(message.chat.id, "Будь ласка, обери період звіту з меню.")
        # Не повертаємося в меню, щоб користувач міг обрати ще раз

    # Видалено дублююче send_welcome(message) поза if-else

def generate_report(period):
    """Генерує текст звіту за заданий період"""
    now = datetime.now()
    
    # Визначаємо діапазон дат
    if period == "Сьогодні":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "Цей тиждень":
        start_date = now - timedelta(days=now.weekday())  # Понеділок
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "Цей місяць":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        return "Невідомий період."
        
    # Оновлюємо кеш, якщо потрібно
    if not update_cache():
        return "❌ Помилка оновлення даних"

    # Використовуємо дані з кешу
    try:
        if not cache["data"]:
            return "📭 Немає записів у таблиці."
        
        data_rows = cache["data"][1:]  # Пропускаємо заголовки
    except Exception as e:
        print(f"Помилка читання кешу: {e}")
        return "❌ Не вдалося прочитати дані."

    # Агрегація
    income_by_cat = defaultdict(float)
    expense_by_cat = defaultdict(float)
    total_income = 0.0
    total_expense = 0.0

    for row in data_rows:
        if len(row) < 5:
            continue  # пропускаємо неповні рядки
        try:
            date_str = row[0].split()[0]  # Беремо тільки дату без часу
            op_type = row[1]
            category = row[2]
            
            # Обробка суми: видаляємо пробіли та замінюємо кому на крапку
            amount_raw = str(row[4]).replace('\xa0', '').replace(' ', '').replace(',', '.')
            amount = float(amount_raw)

            # Перетворюємо дату
            row_date = datetime.strptime(date_str, "%Y-%m-%d")
            if row_date.date() < start_date.date():
                continue  # пропускаємо старі записи

            if op_type == "Дохід":
                income_by_cat[category] += amount
                total_income += amount
            elif op_type == "Розхід":
                expense_by_cat[category] += amount
                total_expense += amount
        except (ValueError, IndexError) as e:
            print(f"Помилка обробки рядка {row}: {e}")
            print(f"Значення суми до обробки: '{row[4]}'")
            continue  # некоректний рядок

    # Формуємо звіт
    if total_income == 0 and total_expense == 0:
        return "📭 За цей період записів немає."

    report = f"📈 **Звіт: {period}**\n\n"

    # Доходи
    if total_income > 0:
        report += "📥 **Доходи**:\n"
        for cat, amt in sorted(income_by_cat.items(), key=lambda x: -x[1]):
            report += f"  • {cat}: **{amt:.2f} грн**\n"
        report += f"  → **Разом доходи**: {total_income:.2f} грн\n\n"

    # Витрати
    if total_expense > 0:
        report += "📤 **Витрати**:\n"
        for cat, amt in sorted(expense_by_cat.items(), key=lambda x: -x[1]):
            report += f"  • {cat}: **{amt:.2f} грн**\n"
        report += f"  → **Разом витрати**: {total_expense:.2f} грн\n\n"

    # Баланс
    balance = total_income - total_expense
    report += f"⚖️ **Баланс**: {balance:.2f} грн"

    return report

def split_message(text, max_length=4000):
    """Розбиває довге повідомлення на частини (Telegram limit ~4096)"""
    if len(text) <= max_length:
        return [text]
    
    # Розбиваємо за логічними блоками (наприклад, по розділах)
    parts = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 <= max_length:
            current += line + "\n"
        else:
            if current:
                parts.append(current)
            current = line + "\n"
    if current:
        parts.append(current)
    return parts

# === ФУНКЦІЇ ГЕЙМІФІКАЦІЇ (тільки виклики, досягнення видалено) ===
def calculate_category_expenses(category, days=7):
    """Розрахувати витрати по категорії за вказаний період"""
    if not refresh_sheets_connection():
        return 0
        
    try:
        all_rows = sheet.get_all_values()[1:]  # Пропускаємо заголовки
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        total = 0
        for row in all_rows:
            try:
                date_str = row[0].split()[0]  # Беремо тільки дату
                row_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if start_date <= row_date <= end_date and row[2] == category:
                    amount = float(str(row[4]).replace('\xa0', '').replace(' ', '').replace(',', '.'))
                    total += amount
            except (ValueError, IndexError):
                continue

        return total
    except Exception as e:
        print(f"Помилка розрахунку витрат: {e}")
        return 0

def complete_challenge(user_id, challenge_id):
    """Завершити виклик успішно"""
    if challenge_id not in user_state[user_id]["active_challenges"]:
        return False
        
    challenge = CHALLENGES[challenge_id]
    user_state[user_id]["active_challenges"][challenge_id]["completed"] = True
    
    # Нараховуємо бали за виклик
    if "points" not in user_state[user_id]:
        user_state[user_id]["points"] = 0
    user_state[user_id]["points"] += challenge["reward"]
    
    # Відправляємо повідомлення про успіх
    message = (
        f"🎉 *Виклик завершено успішно!*\n\n"
        f"{challenge['title']}\n"
        f"Нараховано балів: +{challenge['reward']}"
    )
    bot.send_message(user_id, message, parse_mode="Markdown")
    return True

def get_user_challenges(user_id):
    """Отримати активні виклики користувача"""
    return user_state.get(user_id, {}).get("active_challenges", {})

def start_challenge(user_id, challenge_id):
    """Почати новий виклик"""
    if challenge_id not in CHALLENGES:
        return False
    
    user_challenges = get_user_challenges(user_id)
    if challenge_id in user_challenges:
        return False
    
    if "active_challenges" not in user_state.get(user_id, {}):
        user_state[user_id]["active_challenges"] = {}
    
    # Додаємо виклик з датою початку
    start_date = datetime.now()
    user_state[user_id]["active_challenges"][challenge_id] = {
        "start_date": start_date,
        "end_date": start_date + timedelta(days=CHALLENGES[challenge_id]["duration_days"]),
        "completed": False
    }
    
    challenge = CHALLENGES[challenge_id]
    message = (
        f"🎯 *Новий виклик розпочато!*\n\n"
        f"{challenge['title']}\n"
        f"_{challenge['description']}_\n"
        f"Тривалість: {challenge['duration_days']} днів\n"
        f"Нагорода: {challenge['reward']} балів"
    )
    bot.send_message(user_id, message, parse_mode="Markdown")
    return True

# get_user_achievements, add_achievement, check_achievements — ВИДАЛЕНО

# === ВИБІР ДАТИ ===
@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "choose_date")
def choose_date(message):
    user_id = message.chat.id

    if message.text == "↩️ Назад":
        prev = go_back(user_id)
        if prev == "start":
            send_welcome(message)
        else:
            choose_type(message)
        return

    today = datetime.now().date()
    selected_date = None

    if message.text == "Сьогодні":
        selected_date = today
    elif message.text == "Вчора":
        selected_date = today - timedelta(days=1)
    elif message.text == "Ввести дату":
        set_user_step(user_id, "enter_custom_date")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("↩️ Назад")
        bot.send_message(
            user_id,
            "Введіть дату у форматі: **ДД.ММ.РРРР**\nНаприклад: `04.11.2025`",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return
    else:
        bot.send_message(user_id, "Будь ласка, обери дату з меню.")
        return

    # Зберігаємо дату у форматі "YYYY-MM-DD"
    set_user_data(user_id, "date", selected_date.strftime("%Y-%m-%d"))
    proceed_to_category(user_id)

def proceed_to_category(user_id):
    """Переходимо до вибору категорії"""
    op_type = get_user_data(user_id, "type")
    set_user_step(user_id, "choose_category")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for cat in CATEGORIES[op_type]:
        markup.add(cat)
    markup.add("↩️ Назад")
    bot.send_message(user_id, f"Обери категорію для {op_type.lower()}у:", reply_markup=markup)

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "enter_custom_date")
def enter_custom_date(message):
    user_id = message.chat.id

    if message.text == "↩️ Назад":
        # Повертаємося до вибору дати
        set_user_step(user_id, "choose_date")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Сьогодні", "Вчора", "Ввести дату")
        markup.add("↩️ Назад")
        bot.send_message(user_id, "Вибери дату операції:", reply_markup=markup)
        return

    # Перевіряємо формат ДД.ММ.РРРР
    try:
        date_obj = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        # Опціонально: заборонити майбутні дати
        if date_obj > datetime.now().date():
            bot.send_message(user_id, "❌ Дата не може бути у майбутньому. Спробуй ще раз.")
            return
        set_user_data(user_id, "date", date_obj.strftime("%Y-%m-%d"))
        proceed_to_category(user_id)
    except ValueError:
        bot.send_message(user_id, "⚠️ Невірний формат дати.\nВведіть: **ДД.ММ.РРРР** (наприклад: `04.11.2025`)", parse_mode="Markdown")

# === ВИБІР КАТЕГОРІЇ ===   
@bot.message_handler(func=lambda m: user_state.get(m.chat.id, {}).get("step") == "choose_category")
def choose_category(message):
    if message.text == "↩️ Назад":
        send_welcome(message)
        return

    category = message.text
    if category not in CATEGORIES["Дохід"] + CATEGORIES["Розхід"]:
        bot.send_message(message.chat.id, "❌ Невірна категорія. Спробуй ще раз.")
        return

    user_state[message.chat.id]["category"] = category

    # Чи є підкатегорії?
    if category in SUBCATEGORIES:
        user_state[message.chat.id]["step"] = "choose_subcategory"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for sub in SUBCATEGORIES[category]:
            markup.add(sub)
        markup.add("Без підкатегорії", "↩️ Назад")
        bot.send_message(message.chat.id, "Обери підкатегорію:", reply_markup=markup)
    else:
        user_state[message.chat.id]["subcategory"] = ""
        user_state[message.chat.id]["step"] = "enter_amount"
        bot.send_message(message.chat.id, "Введіть суму (можна з описом):\nНаприклад: `500` або `500 Премія`")

# === ВИБІР ПІДКАТЕГОРІЇ ===
@bot.message_handler(func=lambda m: user_state.get(m.chat.id, {}).get("step") == "choose_subcategory")
def choose_subcategory(message):
    if message.text == "↩️ Назад":
        choose_type(message)  # повертаємося до вибору типу
        return
    if message.text == "Без підкатегорії":
        user_state[message.chat.id]["subcategory"] = ""
    else:
        user_state[message.chat.id]["subcategory"] = message.text

    user_state[message.chat.id]["step"] = "enter_amount"
    bot.send_message(message.chat.id, "Введіть суму (можна з описом):\nНаприклад: `500` або `500 Премія`")

# === ВВЕДЕННЯ СУМИ ===
@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "enter_amount")
def enter_amount(message):
    if message.text == "↩️ Назад":
        send_welcome(message)
        return

    # Розбираємо: "сума [опис]"
    parts = message.text.strip().split(" ", 1)
    try:
        amount = float(parts[0])
        description = parts[1] if len(parts) > 1 else ""
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ Введіть спочатку суму числом!\nПриклад: `1200` або `1200 ЗП`")
        return

    # Отримуємо дані
    selected_date_str = get_user_data(message.chat.id, "date")
    current_time = datetime.now().strftime("%H:%M")
    date = f"{selected_date_str} {current_time}"
    op_type = get_user_data(message.chat.id, "type")
    category = get_user_data(message.chat.id, "category")
    subcategory = get_user_data(message.chat.id, "subcategory", "")

    # Зберігаємо ОДИН раз
    new_row = [date, op_type, category, subcategory, amount, description]
    if not refresh_sheets_connection():
        bot.send_message(message.chat.id, "❌ Помилка з'єднання з Google Sheets")
        send_welcome(message)
        return

    try:
        sheet.append_row(new_row)
        update_cache(force=True)  # оновлюємо кеш для звітів/графіків
    except Exception as e:
        print(f"Помилка запису: {e}")
        bot.send_message(message.chat.id, "❌ Помилка збереження. Спробуйте ще раз.")
        send_welcome(message)
        return

    # Підтвердження
    bot.send_message(
        message.chat.id,
        f"✅ Записано!\nТип: {op_type}\nКатегорія: {category}\n"
        f"Підкатегорія: {subcategory or '—'}\nСума: {amount} грн\nОпис: {description or '—'}"
    )

    # Перевірки (бюджет тощо) — досягнення видалено
    if op_type == "Розхід":
        check_budget_limits(message.chat.id, category, amount)
    # check_achievements(message.chat.id)  # Видалено

    send_welcome(message)

# === 1. Визначення функції видалення ===
def delete_last_record(message):
    if not refresh_sheets_connection():
        bot.send_message(message.chat.id, "❌ Помилка з'єднання з Google Sheets")
        send_welcome(message)
        return
        
    try:
        all_rows = sheet.get_all_values()
        if len(all_rows) <= 1:
            bot.send_message(message.chat.id, "📭 Немає записів для видалення.")
            send_welcome(message)
            return

        last_row = all_rows[-1]
        while len(last_row) < 6:
            last_row.append("")
            
        date, op_type, category, subcat, amount, desc = last_row[:6]
        subcat = subcat.strip() if subcat.strip() else "—"
        desc = desc.strip() if desc.strip() else "—"
        amount = amount.strip() if amount.strip() else "0"

        confirm_text = (
            f"🗑️ *Видалення запису*\n\n"
            f"📅 Дата: {date}\n"
            f"📊 Тип: {op_type}\n"
            f"🏷️ Категорія: {category}"
        )
        if subcat != "—":
            confirm_text += f" → {subcat}"
        confirm_text += f"\n💰 Сума: {amount} грн\n📝 Опис: {desc}\n\n"
        confirm_text += "Ви впевнені?"

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Так, видалити", "↩️ Скасувати")
        bot.send_message(message.chat.id, confirm_text, reply_markup=markup, parse_mode="Markdown")

        row_index = len(all_rows)
        set_user_data(message.chat.id, "delete_row_index", row_index)
        set_user_step(message.chat.id, "confirm_delete")

    except Exception as e:
        print(f"Помилка при видаленні: {e}")
        bot.send_message(message.chat.id, "❌ Не вдалося завантажити записи.")
        send_welcome(message)


# === 2. Обробник кнопки (викликає функцію) ===
@bot.message_handler(func=lambda m: m.text == "🗑️ Видалити останнє")
def handle_delete_button(message):
    delete_last_record(message)  # тепер ця функція існує!


@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "confirm_delete")
def confirm_delete(message):
    if message.text == "↩️ Скасувати":
        bot.send_message(message.chat.id, "Видалення скасовано.")
        send_welcome(message)
        return

    if message.text == "Так, видалити":
        try:
            row_index = get_user_data(message.chat.id, "delete_row_index")
            if row_index and isinstance(row_index, int):
                # Оновлюємо кеш перед видаленням
                if update_cache():
                    # Видаляємо з кешу
                    if len(cache["data"]) >= row_index:
                        deleted_row = cache["data"].pop(row_index - 1)  # -1 бо індекси в Google Sheets починаються з 1
                        
                        # Оновлюємо статистику
                        try:
                            date_str = deleted_row[0].split()[0]
                            date = datetime.strptime(date_str, "%Y-%m-%d")
                            month_key = date.strftime("%Y-%m")
                            
                            op_type = deleted_row[1]
                            category = deleted_row[2]
                            amount_str = deleted_row[4].replace('\xa0', '').replace(' ', '').replace(',', '.')
                            amount = float(amount_str)
                            
                            if op_type == "Дохід":
                                cache["monthly_stats"][month_key]["income"] -= amount
                            else:
                                cache["monthly_stats"][month_key]["expense"] -= amount
                            
                            cache["category_stats"][month_key][category] -= amount
                        except (ValueError, IndexError) as e:
                            print(f"Помилка оновлення статистики при видаленні: {e}")
                    
                    # Видаляємо з Google Sheets
                    sheet.delete_rows(row_index)
                    bot.send_message(message.chat.id, "✅ Запис успішно видалено!")
                else:
                    bot.send_message(message.chat.id, "❌ Помилка оновлення даних")
            else:
                bot.send_message(message.chat.id, "❌ Помилка: невірний індекс запису.")
        except Exception as e:
            print(f"Помилка видалення: {e}")
            bot.send_message(message.chat.id, "❌ Не вдалося видалити запис. Перевірте доступ до таблиці.")
    else:
        bot.send_message(message.chat.id, "Будь ласка, оберіть дію з меню.")
        return

    send_welcome(message)
            

# === Періодична обробка batch-оновлень ===
def process_updates():
    """Періодично обробляє batch-оновлення"""
    while True:
        try:
            process_batch_updates()
        except Exception as e:
            print(f"Помилка при обробці batch-оновлень: {e}")
        time.sleep(cache["batch_update_interval"])

# === ФУНКЦІЇ ДЛЯ ГРАФІКІВ ===
def create_expense_pie_chart(month=None):
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    if not update_cache(force=True):
        print("❌ Не вдалося оновити кеш для графіка")
        return None
    
    try:
        expenses = defaultdict(float)
        data_rows = [row for row in cache["data"][1:] if len(row) >= 5]  # Фільтр неповних
        for row in data_rows:
            date_str = row[0].split()[0]
            row_month = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m")
            
            if row_month == month and row[1] == "Розхід":
                category = row[2]
                amount = float(str(row[4]).replace('\xa0', '').replace(' ', '').replace(',', '.'))
                expenses[category] += amount
                expenses[category] += amount  # Дублікат, видалити якщо не потрібно
        
        if sum(expenses.values()) == 0:
            print("⚠️ Немає витрат для pie chart")
            return None
        
        # ... (решта без змін)
        plt.figure(figsize=(10, 8))
        plt.clf()
        
        labels = [cat for cat, _ in sorted(expenses.items(), key=lambda x: x[1], reverse=True)]
        sizes = [amt for _, amt in sorted(expenses.items(), key=lambda x: x[1], reverse=True)]
        
        plt.pie(sizes, labels=labels, autopct='%1.1f%%')
        plt.title(f'Розподіл витрат за {month}')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close()
        print("✅ Pie chart створено")  # Лог
        return buf
    except Exception as e:
        print(f"❌ Помилка pie chart: {e}")
        return None

def create_expense_trend_chart(months=6):
    """Створює графік трендів витрат по місяцях"""
    if not update_cache():
        return None
    
    try:
        # Підготовка даних
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * months)
        
        # Створюємо DataFrame для зручної роботи з даними
        dates = []
        amounts = []
        categories = []
        
        for row in cache["data"][1:]:  # Пропускаємо заголовки
            try:
                date = datetime.strptime(row[0].split()[0], "%Y-%m-%d")
                if start_date <= date <= end_date and row[1] == "Розхід":
                    dates.append(date)
                    amount = float(row[4].replace('\xa0', '').replace(' ', '').replace(',', '.'))
                    amounts.append(amount)
                    categories.append(row[2])
            except (ValueError, IndexError):
                continue
        
        if not dates:
            return None
        
        df = pd.DataFrame({
            'date': dates,
            'amount': amounts,
            'category': categories
        })
        
        # Групуємо по місяцях і категоріях
        monthly = df.groupby([pd.Grouper(key='date', freq='M'), 'category'])['amount'].sum().unstack()
        
        # Створюємо графік
        plt.figure(figsize=(12, 6))
        plt.clf()
        
        # Малюємо лінії для кожної категорії
        for column in monthly.columns:
            plt.plot(monthly.index, monthly[column], marker='o', label=column)
        
        plt.title('Тренди витрат по категоріях')
        plt.xlabel('Місяць')
        plt.ylabel('Сума (грн)')
        plt.xticks(rotation=45)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True)
        
        # Зберігаємо в буфер
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Помилка створення графіка трендів: {e}")
        return None

def create_budget_progress_chart():
    if not update_cache(force=True):
        print("❌ Кеш не оновлено для budget chart")
        return None
    
    try:
        current_month = datetime.now().strftime("%Y-%m")
        
        # Збираємо поточні витрати
        current_expenses = defaultdict(float)
        for row in cache["data"][1:]:
            date_str = row[0].split()[0]
            row_month = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m")
            
            if row_month == current_month and row[1] == "Розхід":
                category = row[2]
                amount = float(row[4].replace('\xa0', '').replace(' ', '').replace(',', '.'))
                current_expenses[category] += amount
        
        # Створюємо графік для категорій з встановленими лімітами
        categories = []
        current_amounts = []
        limits = []
        
        for category, limit in BUDGET_LIMITS["monthly"].items():
            if limit > 0:  # Тільки категорії з встановленими лімітами
                categories.append(category)
                current_amounts.append(current_expenses[category])
                limits.append(limit)
        
        if not categories:
            return None
        
        # Створюємо графік
        plt.figure(figsize=(12, 6))
        plt.clf()
        
        x = range(len(categories))
        width = 0.35
        
        plt.bar(x, current_amounts, width, label='Поточні витрати')
        plt.bar([i + width for i in x], limits, width, label='Ліміт')
        
        plt.xlabel('Категорії')
        plt.ylabel('Сума (грн)')
        plt.title('Прогрес витрат відносно бюджету')
        plt.xticks([i + width/2 for i in x], categories, rotation=45)
        plt.legend()
        
        # Зберігаємо в буфер
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Помилка створення графіка прогресу бюджету: {e}")
        return None

# === ОБРОБНИКИ ГРАФІКІВ ТА БЮДЖЕТУ ===
@bot.message_handler(func=lambda m: m.text == "📈 Графіки")
def show_charts_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        "🥧 Структура витрат",
        "📊 Тренди витрат",
        "📈 Прогрес бюджету"
    )
    markup.add("↩️ Назад")
    bot.send_message(message.chat.id, "Оберіть тип графіка:", reply_markup=markup)
    set_user_step(message.chat.id, "choose_chart")

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "choose_chart")
def handle_chart_choice(message):
    if message.text == "↩️ Назад":
        send_welcome(message)
        return
        
    chart_buf = None
    if message.text == "🥧 Структура витрат":
        chart_buf = create_expense_pie_chart()
    elif message.text == "📊 Тренди витрат":
        chart_buf = create_expense_trend_chart()
    elif message.text == "📈 Прогрес бюджету":
        chart_buf = create_budget_progress_chart()
    
    if chart_buf:
        bot.send_photo(message.chat.id, chart_buf)
    else:
        bot.send_message(message.chat.id, "❌ Не вдалося створити графік. Можливо, недостатньо даних.")
    
    send_welcome(message)

@bot.message_handler(func=lambda m: m.text == "💼 Бюджет")
def show_budget_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        "📝 Встановити ліміт",
        "👀 Переглянути ліміти",
        "🔄 Скинути ліміти"
    )
    markup.add("↩️ Назад")
    bot.send_message(message.chat.id, "Оберіть дію:", reply_markup=markup)
    set_user_step(message.chat.id, "budget_menu")

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "budget_menu")
def handle_budget_menu(message):
    if message.text == "↩️ Назад":
        send_welcome(message)
        return
        
    if message.text == "📝 Встановити ліміт":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for category in CATEGORIES["Розхід"]:
            markup.add(category)
        markup.add("↩️ Назад")
        bot.send_message(message.chat.id, "Оберіть категорію для встановлення ліміту:", reply_markup=markup)
        set_user_step(message.chat.id, "choose_limit_category")
        return  # ФІКС: return, щоб не йти в send_welcome
    
    elif message.text == "👀 Переглянути ліміти":
        update_cache(force=True)  # Force
        if not BUDGET_LIMITS["monthly"]:
            bot.send_message(message.chat.id, "Ліміти ще не встановлені. Встановіть їх через '📝 Встановити ліміт'.")
        else:
            limits_text = "📊 *Встановлені ліміти:*\n\n"
            current_month = datetime.now().strftime("%Y-%m")
            for category, limit in BUDGET_LIMITS["monthly"].items():
                current_expenses = sum(
                    float(row[4].replace('\xa0', '').replace(' ', '').replace(',', '.'))
                    for row in cache["data"][1:]
                    if (len(row) >= 5 and row[1] == "Розхід" and row[2] == category and
                        datetime.strptime(row[0].split()[0], "%Y-%m-%d").strftime("%Y-%m") == current_month)
                )
                progress = (current_expenses / limit * 100) if limit > 0 else 0
                limits_text += f"*{category}*:\nЛіміт: {limit:,.2f} грн\nВитрачено: {current_expenses:,.2f} грн ({progress:.1f}%)\n\n"
            
            bot.send_message(message.chat.id, limits_text, parse_mode="Markdown")
        send_welcome(message)
        return
    
    elif message.text == "🔄 Скинути ліміти":
        BUDGET_LIMITS["monthly"].clear()
        save_budget_limits()  # Зберігаємо порожній стан
        bot.send_message(message.chat.id, "✅ Всі ліміти скинуто!")
        send_welcome(message)
        return
    
    # ФІКС: Видалено send_welcome(message) поза if-ами, бо воно ламало multi-step

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "choose_limit_category")
def handle_limit_category(message):
    if message.text == "↩️ Назад":
        show_budget_menu(message)
        return
        
    if message.text in CATEGORIES["Розхід"]:
        set_user_data(message.chat.id, "limit_category", message.text)
        bot.send_message(message.chat.id, 
            "Введіть місячний ліміт для категорії (лише число):\n"
            "Наприклад: 1000"
        )
        set_user_step(message.chat.id, "enter_limit")
    else:
        bot.send_message(message.chat.id, "❌ Невірна категорія. Спробуйте ще раз.")

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "enter_limit")
def handle_limit_amount(message):
    try:
        limit = float(message.text.replace(' ', ''))
        category = get_user_data(message.chat.id, "limit_category")
        
        if limit <= 0:
            bot.send_message(message.chat.id, "❌ Ліміт повинен бути більше 0.")
            return
            
        BUDGET_LIMITS["monthly"][category] = limit
        save_budget_limits()  # Зберігаємо в Sheets
        bot.send_message(
            message.chat.id,
            f"✅ Встановлено ліміт {limit:,.2f} грн для категорії {category}"
        )
        
        # Додано: оновлення кешу перед розрахунком
        update_cache()
        # Перевіряємо поточні витрати відносно нового ліміту
        current_month = datetime.now().strftime("%Y-%m")
        current_expenses = sum(
            float(row[4].replace('\xa0', '').replace(' ', '').replace(',', '.'))
            for row in cache["data"][1:]
            if (row[1] == "Розхід" and 
                row[2] == category and
                datetime.strptime(row[0].split()[0], "%Y-%m-%d").strftime("%Y-%m") == current_month)
        )
        
        if current_expenses > 0:
            progress = current_expenses / limit * 100
            bot.send_message(
                message.chat.id,
                f"💡 Поточні витрати в категорії: {current_expenses:,.2f} грн ({progress:.1f}% від ліміту)"
            )
    except ValueError:
        bot.send_message(message.chat.id, "❌ Будь ласка, введіть коректне число.")
        return
    
    send_welcome(message)

def check_budget_limits(user_id, category, amount):
    """Перевіряє ліміти бюджету при додаванні нових витрат"""
    # Додано: оновлення кешу перед перевіркою
    update_cache()
    if category not in BUDGET_LIMITS["monthly"]:
        return
        
    limit = BUDGET_LIMITS["monthly"][category]
    current_month = datetime.now().strftime("%Y-%m")
    
    current_expenses = sum(
        float(row[4].replace('\xa0', '').replace(' ', '').replace(',', '.'))
        for row in cache["data"][1:]
        if (row[1] == "Розхід" and 
            row[2] == category and
            datetime.strptime(row[0].split()[0], "%Y-%m-%d").strftime("%Y-%m") == current_month)
    )
    
    new_total = current_expenses + amount
    if new_total > limit:
        bot.send_message(
            user_id,
            f"⚠️ *Увага!* Ви перевищили місячний ліміт в категорії *{category}*\n"
            f"Ліміт: {limit:,.2f} грн\n"
            f"Поточні витрати: {new_total:,.2f} грн\n"
            f"Перевищення: {(new_total - limit):,.2f} грн",
            parse_mode="Markdown"
        )
    elif new_total >= limit * 0.8:  # Попередження при досягненні 80% ліміту
        bot.send_message(
            user_id,
            f"⚠️ Ви використали {(new_total/limit*100):.1f}% ліміту в категорії *{category}*\n"
            f"Залишилось: {(limit - new_total):,.2f} грн",
            parse_mode="Markdown"
        )

# === Запуск ===
if __name__ == "__main__":
    print("💰 Бот із категоріями запущено!")
    
    # Запускаємо обробку batch-оновлень у окремому потоці
    updates_thread = Thread(target=process_updates, daemon=True)
    updates_thread.start()
    
    bot.polling(none_stop=True)