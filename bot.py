import telebot
from telebot import types
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime, timedelta
import re

# === НАЛАШТУВАННЯ ===
BOT_TOKEN = "8509328290:AAFhXhXVl49RyQhrBKnQpYbDIlFODVi03Xc"
SPREADSHEET_NAME = "WestCamp"
CREDENTIALS_FILE = "credentials.json"

# === КОНФІГ ДЛЯ ТАБОРУ ===
CONFIG_OTHER = {
    'periods': {
        'lito_2025': "Літо 2025",
        'osin_2025': "Осінь 2025",
        'zima_2026': "Зима 2026",
    },
    'locations': {
        'all': "Операційні витрати на всі локації",
        'vizhnytsia': "Вижниця",
        'lyucha': "Люча",
        'putyla': "Путила",
        'Transfer': "Трансфер",
    },
    'locations_by_period': {
        'lito_2025': ['vizhnytsia', 'lyucha', 'all'],
        'osin_2025': ['putyla', 'all', 'Transfer'],
        'zima_2026': ['lyucha', 'all', 'Transfer'],
    },
    'changes_by_location_period': {
        'lito_2025': {
            'all': ["oper_vytraty", "pover_avans"],
            'vizhnytsia': ["1_zmina", "2_zmina"],
            'lyucha': ["1_zmina", "2_zmina"],
        },
        'osin_2025': {
            'all': ["oper_vytraty", "pover_avans"],
            'putyla': ["1_zmina"],
        },
        'zima_2026': {
            'all': ["oper_vytraty", "pover_avans"],
            'lyucha': ["1_zmina", "2_zmina"],
        },
    },
    'categories_by_change': {
        '1 - Зміна': ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору'],
        '2 - Зміна': ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору'],
        'Операційні витрати': ['Маркетинг', 'Зарплата', 'Реклама'],
        'Повернення авансів': ['Повернення коштів', 'Аванс повернуто'],
    },
    'subcategories_by_category': {
        'Розваги': ['Гонорар', 'Оплата дороги', 'Харчування', 'Автобуси', 'Дод. витрати', 'реквізит', 'музеї'],
        'Команда': ['Зарплата', 'Проживання і харчування', 'Трансфер команди', 'Дод. витрати'],
        'Проживання дітей': ['За всю зміну', 'Дод. витрати'],
        'Додаткові витрати': ['Канцтовари', 'Медикаменти', 'Паливо', 'Декор', 'Настілки', 'Інші витрати', 'Мерч'],
        'Маркетинг': ['Реклама', 'SMM', 'Промо', 'Креативи'],
        'Зарплата': ['Відділ продажів', 'Адмін', 'Директор', 'Тех. працівники'],
    },
}

# Мапінги
CHANGE_ASCII_TO_UKR = {
    "1_zmina": "1 - Зміна", 
    "2_zmina": "2 - Зміна", 
    "oper_vytraty": "Операційні витрати", 
    "pover_avans": "Повернення авансів"
}
CHANGE_UKR_TO_ASCII = {v: k for k, v in CHANGE_ASCII_TO_UKR.items()}

ACCOUNT_MAP = {
    "радул і": "ФОП №1 Радул І.І.", "1": "ФОП №1 Радул І.І.", 
    "радул я": "ФОП №2 Радул Я.Ю.", "2": "ФОП №2 Радул Я.Ю.", 
    "скидан": "ФОП №3 Скидан Х.С.", "3": "ФОП №3 Скидан Х.С.", 
    "фоп досієвич": "ФОП №4 Досієвич В.П.", "4": "ФОП №4 Досієвич В.П.", 
    "фоп демедюк": "ФОП №5 Демедюк Л.В.", "5": "ФОП №5 Демедюк Л.В.", 
    "фоп спельчук а": "ФОП №6 Спельчук А.А.", "6": "ФОП №6 Спельчук А.А.", 
    "фоп спельчук о": "ФОП №7 Спельчук О.Ю.", "7": "ФОП №7 Спельчук О.Ю.", 
    "8": "ФОП №8 Чолан Л.", "Чолан": "ФОП №8 Чолан Л."
}

# Мапінг категорій для дивідендів
DIVIDENDS_CATEGORIES = {
    "Ваня": ["Мантра", "Особисте Ваня", "Нові проекти Ваня", "Синичка Ваня"],
    "Яна": ["Особисте Яна", "Нові проекти Яна", "Синичка Яна"]
}

# === ГЛОБАЛЬНИЙ СТАН ===
user_state = {}

# === ПІДКЛЮЧЕННЯ ДО GOOGLE SHEETS ===
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']  # ✅ Тільки необхідний scope

def refresh_sheets_connection():
    global SHEET_MAP
    try:
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        client = gspread.authorize(creds)
        book = client.open(SPREADSHEET_NAME)
        SHEET_MAP = {'shift_expenses': book.worksheet("ShiftExpenses")}
        if not SHEET_MAP['shift_expenses'].get_all_values():
            SHEET_MAP['shift_expenses'].append_row([
                "Дата", "Група", "Рахунок", "Період", "Локація", "Категорія витрат", 
                "Зміни", "Категорії", "Дод. категорії", "Дод. інформація", "Сума", "Коментар", "Факт / Прогноз"
            ])
        print("✅ З'єднання з WestCamp успішне!")
        return True
    except Exception as e:
        print(f"❌ Помилка підключення: {e}")
        return False

SHEET_MAP = {}
refresh_sheets_connection()

bot = telebot.TeleBot(BOT_TOKEN)

# === УТИЛІТИ ===
def set_user_data(user_id, key, value):
    user_state[user_id] = user_state.get(user_id, {})
    user_state[user_id][key] = value

def set_user_step(user_id, step):
    user_state[user_id] = user_state.get(user_id, {})
    user_state[user_id]["step"] = step

def get_user_data(user_id, key, default=None):
    return user_state.get(user_id, {}).get(key, default)

def get_user_step(user_id):
    return user_state.get(user_id, {}).get("step", "main_menu")

def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add("Фінансові операції")
    bot.send_message(message.chat.id, "Привіт! Обери:", reply_markup=markup)
    set_user_step(message.chat.id, "main_menu")

# === START ===
@bot.message_handler(commands=['start'])
def start(message):
    send_welcome(message)

# === ФІНАНСОВІ ОПЕРАЦІЇ ===
@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "main_menu" and m.text == "Фінансові операції")
def handle_financial(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Дохід", "Розхід")
    bot.send_message(message.chat.id, "Обери тип операції:", reply_markup=markup)
    set_user_step(message.chat.id, "financial_menu")

# === ДОХІД (заглушка) ===
@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "financial_menu" and m.text == "Дохід")
def handle_income(message):
    bot.send_message(
        message.chat.id, 
        "⚠️ Функція 'Дохід' ще не реалізована для табору. Використовуйте 'Розхід'."
    )
    send_welcome(message)

# === РОЗХІД ===
@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "financial_menu" and m.text == "Розхід")
def handle_expense(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Дивіденди", "Витрати табору")
    markup.add("Податки, Сайт та срм", "↩️ Назад")
    bot.send_message(message.chat.id, "Обери тип розходу:", reply_markup=markup)
    set_user_step(message.chat.id, "choose_expense_type")

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "choose_expense_type")
def choose_expense_type(message):
    user_id = message.chat.id
    if message.text == "↩️ Назад":
        set_user_step(user_id, "financial_menu")
        handle_financial(message)
        return
    
    expense_type = message.text
    set_user_data(user_id, "expense_type", expense_type)
    set_user_data(user_id, "type", "expense")
    
    # Для дивідендів - спрощений флоу (без періоду/локації/зміни)
    if expense_type == "Дивіденди":
        set_user_step(user_id, "enter_date_dividends")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Сьогодні", "Вчора", "Ввести дату")
        markup.add("↩️ Назад")
        bot.send_message(user_id, "📝 Введіть дату (ДД.ММ.РРРР):", reply_markup=markup)
        return
    
    # Для податків - також спрощений флоу
    if expense_type == "Податки, Сайт та срм":
        set_user_step(user_id, "enter_date_taxes")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Сьогодні", "Вчора", "Ввести дату")
        markup.add("↩️ Назад")
        bot.send_message(user_id, "📝 Введіть дату (ДД.ММ.РРРР):", reply_markup=markup)
        return
    
    # Для витрат табору - стандартний флоу
    set_user_step(user_id, "choose_period_expense")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for name in CONFIG_OTHER['periods'].values():
        markup.add(name)
    markup.add("↩️ Назад")
    bot.send_message(user_id, "Обери період:", reply_markup=markup)

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "choose_period_expense")
def choose_period_expense(message):
    user_id = message.chat.id
    if message.text == "↩️ Назад":
        set_user_step(user_id, "choose_expense_type")
        return
    period_name = message.text
    period_key = next(k for k, v in CONFIG_OTHER['periods'].items() if v == period_name)
    set_user_data(user_id, "period", period_key)
    set_user_step(user_id, "choose_location_expense")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    locations = CONFIG_OTHER['locations_by_period'][period_key]
    for loc_key in locations:
        markup.add(CONFIG_OTHER['locations'][loc_key])
    markup.add("↩️ Назад")
    bot.send_message(user_id, "Обери локацію:", reply_markup=markup)

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "choose_location_expense")
def choose_location_expense(message):
    user_id = message.chat.id
    if message.text == "↩️ Назад":
        set_user_step(user_id, "choose_period_expense")
        return
    location_name = message.text
    location_key = next(k for k, v in CONFIG_OTHER['locations'].items() if v == location_name)
    set_user_data(user_id, "location", location_key)
    set_user_step(user_id, "choose_change_expense")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    changes = CONFIG_OTHER['changes_by_location_period'].get(get_user_data(user_id, "period"), {}).get(location_key, [])
    for ch_key in changes:
        markup.add(CHANGE_ASCII_TO_UKR.get(ch_key, ch_key))
    markup.add("↩️ Назад")
    bot.send_message(user_id, "Обери зміну:", reply_markup=markup)

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "choose_change_expense")
def choose_change_expense(message):
    user_id = message.chat.id
    if message.text == "↩️ Назад":
        set_user_step(user_id, "choose_location_expense")
        return
    change_name = message.text
    change_key = CHANGE_UKR_TO_ASCII.get(change_name)
    if not change_key:
        bot.send_message(user_id, "❌ Невідома зміна.")
        return
    set_user_data(user_id, "change", change_key)
    set_user_step(user_id, "choose_category_expense")
    categories = CONFIG_OTHER['categories_by_change'].get(change_name, [])
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for cat in categories:
        markup.add(cat)
    markup.add("↩️ Назад")
    bot.send_message(user_id, "Обери категорію:", reply_markup=markup)

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "choose_category_expense")
def choose_category_expense(message):
    user_id = message.chat.id
    if message.text == "↩️ Назад":
        set_user_step(user_id, "choose_change_expense")
        return
    category = message.text
    set_user_data(user_id, "category", category)
    subcats = CONFIG_OTHER['subcategories_by_category'].get(category, [])
    if subcats:
        set_user_step(user_id, "choose_subcategory_expense")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for sub in subcats:
            markup.add(sub)
        markup.add("Без підкатегорії", "↩️ Назад")
        bot.send_message(user_id, "Обери підкатегорію:", reply_markup=markup)
    else:
        set_user_data(user_id, "subcategory", "")
        set_user_step(user_id, "choose_account_expense")

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "choose_subcategory_expense")
def choose_subcategory_expense(message):
    user_id = message.chat.id
    if message.text == "↩️ Назад":
        set_user_step(user_id, "choose_category_expense")
        return
    subcategory = "" if message.text == "Без підкатегорії" else message.text
    set_user_data(user_id, "subcategory", subcategory)
    set_user_step(user_id, "choose_account_expense")

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "choose_account_expense")
def choose_account_expense(message):
    user_id = message.chat.id
    if message.text == "↩️ Назад":
        if get_user_data(user_id, "subcategory"):
            set_user_step(user_id, "choose_subcategory_expense")
        else:
            set_user_step(user_id, "choose_category_expense")
        return
    account = message.text
    if account in ACCOUNT_MAP:
        account = ACCOUNT_MAP[account]
    set_user_data(user_id, "account", account)
    set_user_step(user_id, "choose_date_expense")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Сьогодні", "Вчора", "Ввести дату")
    markup.add("↩️ Назад")
    bot.send_message(user_id, "Обери дату:", reply_markup=markup)

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "choose_date_expense")
def choose_date_expense(message):
    user_id = message.chat.id
    if message.text == "↩️ Назад":
        set_user_step(user_id, "choose_account_expense")
        return
    today = datetime.now().date()
    if message.text == "Сьогодні":
        selected_date = today
    elif message.text == "Вчора":
        selected_date = today - timedelta(days=1)
    elif message.text == "Ввести дату":
        set_user_step(user_id, "enter_custom_date_expense")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("↩️ Назад")
        bot.send_message(user_id, "Введіть дату (ДД.ММ.РРРР):", reply_markup=markup)
        return
    else:
        bot.send_message(user_id, "Обери з меню.")
        return
    set_user_data(user_id, "date", selected_date.strftime("%d.%m.%Y"))
    set_user_step(user_id, "enter_amount_expense")
    bot.send_message(user_id, "Введіть суму (можна з коментарем):\nНаприклад: `963 цукерки`")

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "enter_custom_date_expense")
def enter_custom_date_expense(message):
    user_id = message.chat.id
    if message.text == "↩️ Назад":
        set_user_step(user_id, "choose_date_expense")
        return
    try:
        date_obj = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        set_user_data(user_id, "date", date_obj.strftime("%d.%m.%Y"))
        set_user_step(user_id, "enter_amount_expense")
        bot.send_message(user_id, "Введіть суму (можна з коментарем):")
    except ValueError:
        bot.send_message(user_id, "⚠️ Невірний формат: ДД.ММ.РРРР")

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "enter_amount_expense")
def enter_amount_expense(message):
    user_id = message.chat.id
    if message.text == "↩️ Назад":
        set_user_step(user_id, "choose_date_expense")
        return
    parts = message.text.strip().split(" ", 1)
    try:
        amount = float(parts[0].replace(' ', '').replace(',', '.'))
        comment = parts[1] if len(parts) > 1 else ""
    except ValueError:
        bot.send_message(user_id, "⚠️ Введіть суму числом!")
        return

    # Формування рядка
    date = get_user_data(user_id, "date")
    group = "Розхід"
    account = get_user_data(user_id, "account")
    period = CONFIG_OTHER['periods'][get_user_data(user_id, "period")]
    location = CONFIG_OTHER['locations'][get_user_data(user_id, "location")]
    category_vitrat = get_user_data(user_id, "category")
    zminy = CHANGE_ASCII_TO_UKR.get(get_user_data(user_id, "change"), "")
    katehorii = get_user_data(user_id, "category")
    dod_katehorii = get_user_data(user_id, "subcategory", "")
    new_row = [
        date, group, account, period, location, category_vitrat, zminy, 
        katehorii, dod_katehorii, "", amount, comment, "Факт"
    ]

    # Запис
    if refresh_sheets_connection():
        SHEET_MAP['shift_expenses'].append_row(new_row)
        bot.send_message(
            user_id, 
            f"✅ Розхід записано!\n"
            f"Тип: {get_user_data(user_id, 'expense_type')}\n"
            f"Дата: {date}\nПеріод: {period}\nЛокація: {location}\n"
            f"Категорія: {category_vitrat}\nЗміна: {zminy}\n"
            f"Сума: {amount} грн\nКоментар: {comment}"
        )
    else:
        bot.send_message(user_id, "❌ Помилка з'єднання.")
    send_welcome(message)

# === ОБРОБКА ДІВІДЕНДІВ ===
@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "enter_date_dividends")
def enter_date_dividends(message):
    user_id = message.chat.id
    if message.text == "↩️ Назад":
        set_user_step(user_id, "choose_expense_type")
        handle_expense(message)
        return
    
    today = datetime.now().date()
    if message.text == "Сьогодні":
        selected_date = today
    elif message.text == "Вчора":
        selected_date = today - timedelta(days=1)
    elif message.text == "Ввести дату":
        set_user_step(user_id, "enter_custom_date_dividends")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("↩️ Назад")
        bot.send_message(user_id, "Введіть дату (ДД.ММ.РРРР):", reply_markup=markup)
        return
    else:
        # Спробувати розпарсити як дату
        try:
            selected_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        except ValueError:
            bot.send_message(user_id, "⚠️ Невірний формат: ДД.ММ.РРРР")
            return
    
    set_user_data(user_id, "date", selected_date.strftime("%d.%m.%Y"))
    set_user_step(user_id, "choose_name_dividends")
    
    # Показуємо вибір імені
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Ваня", "Яна")
    markup.add("↩️ Назад")
    bot.send_message(user_id, "Обери ім'я:", reply_markup=markup)

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "enter_custom_date_dividends")
def enter_custom_date_dividends(message):
    user_id = message.chat.id
    if message.text == "↩️ Назад":
        set_user_step(user_id, "enter_date_dividends")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Сьогодні", "Вчора", "Ввести дату")
        markup.add("↩️ Назад")
        bot.send_message(user_id, "📝 Введіть дату (ДД.ММ.РРРР):", reply_markup=markup)
        return
    
    try:
        date_obj = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        set_user_data(user_id, "date", date_obj.strftime("%d.%m.%Y"))
        set_user_step(user_id, "choose_name_dividends")
        
        # Показуємо вибір імені
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("Ваня", "Яна")
        markup.add("↩️ Назад")
        bot.send_message(user_id, "Обери ім'я:", reply_markup=markup)
    except ValueError:
        bot.send_message(user_id, "⚠️ Невірний формат: ДД.ММ.РРРР")

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "choose_name_dividends")
def choose_name_dividends(message):
    user_id = message.chat.id
    if message.text == "↩️ Назад":
        set_user_step(user_id, "enter_date_dividends")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Сьогодні", "Вчора", "Ввести дату")
        markup.add("↩️ Назад")
        bot.send_message(user_id, "📝 Введіть дату (ДД.ММ.РРРР):", reply_markup=markup)
        return
    
    if message.text not in DIVIDENDS_CATEGORIES:
        bot.send_message(user_id, "❌ Оберіть ім'я з меню (Ваня або Яна).")
        return
    
    name = message.text
    set_user_data(user_id, "dividends_name", name)
    set_user_step(user_id, "choose_category_dividends")
    
    # Показуємо категорії для вибраного імені
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for category in DIVIDENDS_CATEGORIES[name]:
        markup.add(category)
    markup.add("↩️ Назад")
    bot.send_message(user_id, f"Обери категорію для {name}:", reply_markup=markup)

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "choose_category_dividends")
def choose_category_dividends(message):
    user_id = message.chat.id
    if message.text == "↩️ Назад":
        set_user_step(user_id, "choose_name_dividends")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("Ваня", "Яна")
        markup.add("↩️ Назад")
        bot.send_message(user_id, "Обери ім'я:", reply_markup=markup)
        return
    
    name = get_user_data(user_id, "dividends_name")
    if message.text not in DIVIDENDS_CATEGORIES.get(name, []):
        bot.send_message(user_id, f"❌ Оберіть категорію з меню для {name}.")
        return
    
    category = message.text
    set_user_data(user_id, "dividends_category", category)
    set_user_step(user_id, "choose_account_dividends")
    
    # Показуємо вибір ФОП
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for key, value in ACCOUNT_MAP.items():
        if isinstance(key, str) and key.isdigit():
            markup.add(value)
    markup.add("↩️ Назад")
    bot.send_message(user_id, "Обери ФОП:", reply_markup=markup)

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "choose_account_dividends")
def choose_account_dividends(message):
    user_id = message.chat.id
    if message.text == "↩️ Назад":
        set_user_step(user_id, "choose_category_dividends")
        name = get_user_data(user_id, "dividends_name")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for category in DIVIDENDS_CATEGORIES[name]:
            markup.add(category)
        markup.add("↩️ Назад")
        bot.send_message(user_id, f"Обери категорію для {name}:", reply_markup=markup)
        return
    
    account = message.text
    # Перевіряємо чи це значення з ACCOUNT_MAP
    if account not in ACCOUNT_MAP.values():
        # Спробувати знайти в мапі
        account_lower = account.lower()
        found = False
        for key, value in ACCOUNT_MAP.items():
            if isinstance(key, str) and (key.lower() == account_lower or value == account):
                account = value
                found = True
                break
        if not found:
            bot.send_message(user_id, "❌ Невірний ФОП. Оберіть з меню.")
            return
    
    set_user_data(user_id, "account", account)
    set_user_step(user_id, "enter_amount_dividends")
    bot.send_message(
        user_id,
        "Введіть суму та коментар:\n"
        "Наприклад: `5000` або `5000 Коментар`"
    )

@bot.message_handler(func=lambda m: get_user_step(m.chat.id) == "enter_amount_dividends")
def enter_amount_dividends(message):
    user_id = message.chat.id
    if message.text == "↩️ Назад":
        set_user_step(user_id, "choose_account_dividends")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for key, value in ACCOUNT_MAP.items():
            if isinstance(key, str) and key.isdigit():
                markup.add(value)
        markup.add("↩️ Назад")
        bot.send_message(user_id, "Обери ФОП:", reply_markup=markup)
        return
    
    # Парсимо суму та коментар
    parts = message.text.strip().split(" ", 1)
    try:
        amount = float(parts[0].replace(' ', '').replace(',', '.'))
        comment = parts[1] if len(parts) > 1 else ""
    except ValueError:
        bot.send_message(user_id, "⚠️ Введіть суму числом!")
        return
    
    # Формуємо рядок для запису
    date = get_user_data(user_id, "date")
    group = "Розхід"
    account = get_user_data(user_id, "account")
    period = ""  # Для дивідендів період не потрібен
    location = ""  # Для дивідендів локація не потрібна
    category_vitrat = "Дивіденди"
    zminy = ""
    katehorii = get_user_data(user_id, "dividends_category")
    dod_katehorii = ""
    
    new_row = [
        date, group, account, period, location, category_vitrat, zminy,
        katehorii, dod_katehorii, "", amount, comment, "Факт"
    ]
    
    # Запис
    if refresh_sheets_connection():
        SHEET_MAP['shift_expenses'].append_row(new_row)
        name = get_user_data(user_id, "dividends_name")
        bot.send_message(
            user_id,
            f"✅ Дивіденди записано!\n"
            f"Дата: {date}\n"
            f"Ім'я: {name}\n"
            f"Категорія: {katehorii}\n"
            f"ФОП: {account}\n"
            f"Сума: {amount} грн\n"
            f"Коментар: {comment or '—'}"
        )
    else:
        bot.send_message(user_id, "❌ Помилка з'єднання.")
    
    send_welcome(message)

# === НАЗАД ===
@bot.message_handler(func=lambda m: m.text == "↩️ Назад")
def global_back(message):
    current_step = get_user_step(message.chat.id)
    if "expense" in current_step:
        set_user_step(message.chat.id, "financial_menu")
        handle_financial(message)
    else:
        send_welcome(message)

# === ЗАПУСК ===
if __name__ == "__main__":
    print("💰 Бот для табору запущено!")
    bot.polling(none_stop=True)