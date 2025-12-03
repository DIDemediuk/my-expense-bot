import re
import datetime
import os
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler
from collections import defaultdict
import unicodedata
from handlers.main_handler import handle_callback


from handlers.expense_handler import (
    simplified_expense_flow,
    handle_simple_date,
    handle_simple_manual_date,
    handle_simple_period,
    handle_simple_subcategory,
    handle_simple_amount,
    handle_simple_comment,
    WAITING_SIMPLE_DATE,
    WAITING_SIMPLE_MANUAL_DATE,
    WAITING_SIMPLE_PERIOD,
    WAITING_SIMPLE_SUBCATEGORY,
    WAITING_SIMPLE_AMOUNT,
    WAITING_SIMPLE_COMMENT,
    USER_ROLES
)

conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_callback)],  # твій основний обробник
    states={
        WAITING_SIMPLE_DATE: [CallbackQueryHandler(handle_simple_date)],
        WAITING_SIMPLE_MANUAL_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_simple_manual_date)],
        WAITING_SIMPLE_PERIOD: [CallbackQueryHandler(handle_simple_period)],
        WAITING_SIMPLE_SUBCATEGORY: [CallbackQueryHandler(handle_simple_subcategory)],
        WAITING_SIMPLE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_simple_amount)],
        WAITING_SIMPLE_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_simple_comment)],
    },
    fallbacks=[],
)



load_dotenv()
logging.basicConfig(level=logging.INFO)
# Базове налаштування (INFO для того коду)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Відфільтруй спам від httpx і telegram (лише WARNING+)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)

load_dotenv()

# ---------------------------
# 🔹 Google Sheets налаштування
# ---------------------------
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS_FILE = os.getenv('GOOGLE_CREDS_FILE', 'credentials.json')
CREDS = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
GS_CLIENT = gspread.authorize(CREDS)
SHEET_BOOK = GS_CLIENT.open("WestCamp")

# Словник аркушів
SHEET_MAP = {
    'dividends': SHEET_BOOK.worksheet("Dividends"),
    'other': SHEET_BOOK.worksheet("ShiftExpenses"),
}

def get_sheet_by_type(expense_type: str):
    return SHEET_MAP.get(expense_type, SHEET_MAP['dividends'])

# Колонки для dividends (6)
DIV_HEADERS = ['Дата', 'Джерело', 'Власник', 'Категорія', 'Сума', 'Примітка']

# Колонки для other (12)
OTHER_HEADERS = [
    "Дата",
    "Група",
    "Рахунок",
    "Період",
    "Локація",
    "Категорія витрат",
    "Зміни",
    "Категорії",
    "Дод. категорії",
    "Дод. інформація",
    "Сума",
    "Коментар",
    "Факт / Прогноз"
]

# ---------------------------
# 🔹 Конфіг для залежностей 'other'
# ---------------------------
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
        'lito_2025': ['vizhnytsia', 'lyucha', 'all'],  # Літо: Вижниця + Люча
        'osin_2025': ['putyla','all', 'Transfer'],  # Осінь: всі
        'zima_2026': ['lyucha', 'all', 'Transfer'],  # Зима: тільки Путила
    },

    'changes_by_location_period': {  # ← НОВЕ: Зміни залежно від ПЕРІОД + ЛОКАЦІЯ (гнучко!)
        'lito_2025': {  # Додано для 'all': тільки "Операційні витрати" і "Повернення авансів"
            'all': ["oper_vytraty", "pover_avans"],
            'vizhnytsia': ["1_zmina", "2_zmina"],  # Приклад: стандартні для конкретної локації (якщо потрібно)
            'lyucha': ["1_zmina", "2_zmina"],
        },
        'osin_2025': {  # Осінь (як раніше)
            'all': ["oper_vytraty", "pover_avans"],  # Зафіксовано для 'all'
            'putyla': ["1_zmina"],  # Тільки 1 для Осінь + Путила
        },
        'zima_2026': {  # Зима (як раніше)
            'all': ["oper_vytraty", "pover_avans"],  # Зафіксовано для 'all'
            'lyucha': ["1_zmina", "2_zmina"],  # 2 зміни
        },
    },

    # Нове: Категорії для Трансферу (без кроку "Зміна")
    'categories_by_location': {
        'Transfer': {
            'Укрзалізниця': ['квитки', 'інші витрати'],
            'Автобуси': ['До локації', 'З локації', 'дод. витрати'],
            'Заробітна плата': ['Олександра', 'Ліза', 'інші'],
            'Дод. витрати': [],  # Без підкатегорій
        }
    },

    'changes': [
        "1 - Зміна",
        "2 - Зміна",
        "3 - Зміна",
        "4 - Зміна",
        "5 - Зміна",
        "6 - Зміна",
        "7 - Зміни",
        "Повернення авансів"
    ],
    
    'categories_by_change': {
        '1 - зміна': ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору'],
        '2 - зміна': ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору'],
        '3 - зміна': ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору'],
        '4 - зміна': ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору'],
        '5 - зміна': ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору'],
        '6 - зміна': ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору'],
        '7 - зміна': ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору'],
        'операційні витрати': ['Маркетинг', 'Зарплата', 'Реклама'],
        'повернення авансів': ['Повернення коштів', 'Аванс повернуто'],
    },
    'subcategories_by_category': {
        'розваги': ['Гонорар', 'Оплата дороги', 'Харчування', 'Автобуси', 'Дод. витрати', 'реквізит', 'музеї'],
        'команда': ['Зарплата', 'Проживання і харчування', 'Трансфер команди', 'Дод. витрати'],
        'проживання дітей': ['За всю зміну', 'Дод. витрати'],
        'додаткові витрати': ['Канцтовари', 'Медикаменти', 'Паливо', 'Декор', 'Настілки', 'Інші витрати', 'Мерч'], 
        'зарплата': [
            'Відділ продажів', 
            'Адмін', 
            'Директор',  # ← Додано: Директор
            'Тех. працівники'  # ← Додано: Тех. працівники (ширша підкатегорія для ЗП)
        ],
        'логістика': ['Транспорт', 'Склад'],
        'повернення коштів': ['Аванс 1', 'Аванс 2'],
        'змінa 1': ['Деталь 1', 'Деталь 2'],
        # Можна додати ще ширші підкатегорії, наприклад:
        'маркетинг': ['Реклама', 'SMM', 'Промо', 'Креативи'],  # Якщо потрібно для Маркетингу
    },
    'subsubcategories_by_subcategory': {  # ← НОВЕ: Третій рівень для конкретних підпунктів
        'відділ продажів': ['Яна', 'Віра', 'Соня'],
        'директор': ['Олег', 'Леся'],
        # Можна додати більше, наприклад:
        # 'адмін': ['Ім\'я1', 'Ім\'я2'],
    },
    'changes_by_subcategory': {
        'реклама': "Рекламна кампанія",
        'дизайн': "Дизайн мерчу",
    }
}

# ---------------------------
# 🔹 ASCII maps для callback_data
# ---------------------------
PERIOD_MAP = {
    'lito_2025': 'lito_2025',
    'osin_2025': 'osin_2025',
    'zima_2026': 'zima_2026',
}

CHANGE_ASCII_TO_UKR = {
    "1_zmina": "1 - Зміна",
    "2_zmina": "2 - Зміна",
    
    "oper_vytraty": "Операційні витрати",
    "pover_avans": "Повернення авансів"
}

CAT_UKR_TO_ASCII = {
    "Зміна 1": "zmina1",
    "Зміна 1a": "zmina1a",
    "Зміна 2": "zmina2",
    "Зміна 2b": "zmina2b",
    "Зміна до 7": "zmina_do7",
    "Зміна 7c": "zmina7c",
    "Розваги": "rozvagy",
    "Команда": "komanda",
    "Проживання дітей": "prozhivanie_ditey",
    "Додаткові витрати": "dodatkovi_vytraty",
    "Маркетинг": "marketynh",
    "Зарплата": "zarplata",
    "Логістика": "logistyka",
    "Повернення коштів": "pover_koshtiv",
    "Аванс повернуто": "avans_pover",
    # Нові для Трансферу
    "Укрзалізниця": "ukrzaliznytsia",
    "Автобуси": "avtobusy",
    "Заробітна плата": "zarobitna_plata",
    "Дод. витрати": "dod_vytraty",
}

CAT_ASCII_TO_UKR = {v: k for k, v in CAT_UKR_TO_ASCII.items()}

SUB_UKR_TO_ASCII = {
    "Реклама": "reklama",
    "Дизайн": "dizayn",
    "Відділ продажів": "vidpil_prodazhiv",
    "Адмін": "admin",
    "Транспорт": "transport",
    "Склад": "sklad",
    "Аванс 1": "avans1",
    "Аванс 2": "avans2",
    "Деталь 1": "detal1",
    "Деталь 2": "detal2",
    "Підготовка": "pidhotovka",
    "Зарплата": "zarplata",
    "Проживання і харчування": "prozhivanie_i_kharchuvannia",
    "Дод. витрати": "dod_vytraty",
    # Нові для Rozvagy та інших
    "Гонорар": "honorar",
    "Оплата дороги": "oplata_dorohy",
    "Харчування": "kharchuvannia",
    "Автобуси": "avtobusy",
    "реквізит": "rekvizyt",
    "музеї": "muzei",
    "Трансфер команди": "transfer_komandy",
    "За всю зміну": "za_vsyu_zminu",
    "Канцтовари": "kanctovary",
    "Медикаменти": "medykamenty",
    "Паливо": "palyvo",
    "Декор": "dekor",
    "Настілки": "nastilky",
    "Інші витрати": "inshi_vytraty",
    "Мерч": "merch",
    # Нові для Трансферу
    "квитки": "kvytky",
    "інші витрати": "inshi_vytraty",
    "До локації": "do_lokatsii",
    "З локації": "z_lokatsii",
    "дод. витрати": "dod_vytraty",
    "Олександра": "oleksandra",
    "Ліза": "liza",
    "інші": "inshi",
    # ← НОВІ: Для ширших підкатегорій ЗП
    "Директор": "dyrektor",
    "Тех. працівники": "tekh_pratsivnyky",
}

SUB_ASCII_TO_UKR = {v: k for k, v in SUB_UKR_TO_ASCII.items()}

# ← НОВІ: ASCII maps для суб-підкатегорій (третій рівень)
SUBSUB_UKR_TO_ASCII = {
    "Яна": "yana",
    "Віра": "vira",
    "Соня": "sonya",
    "Олег": "oleg",
    "Леся": "lesya",
}

SUBSUB_ASCII_TO_UKR = {v: k for k, v in SUBSUB_UKR_TO_ASCII.items()}

# ---------------------------
# 🔹 Словник ФОПів
# ---------------------------
ACCOUNT_MAP = {
    "радул і": "ФОП №1 Радул І.І.",
    "1": "ФОП №1 Радул І.І.",
    "радул я": "ФОП №2 Радул Я.Ю.",
    "2": "ФОП №2 Радул Я.Ю.",
    "скидан": "ФОП №3 Скидан Х.С.",
    "фоп скидан": "ФОП №3 Скидан Х.С.",
    "3": "ФОП №3 Скидан Х.С.",
    "фоп досієвич": "ФОП №4 Досієвич В.П.",
    "4": "ФОП №4 Досієвич В.П.",
    "фоп демедюк": "ФОП №5 Демедюк Л.В.",
    "5": "ФОП №5 Демедюк Л.В.",
    "фоп спельчук а": "ФОП №6 Спельчук А.А.",
    "6": "ФОП №6 Спельчук А.А.",
    "фоп спельчук о": "ФОП №7 Спельчук О.Ю.",
    "7": "ФОП №7 Спельчук О.Ю.",
    "радул": "ФОП №1 Радул І.І.",
    "досієвич": "ФОП №4 Досієвич В.П.",
    "демедюк": "ФОП №5 Демедюк Л.В.",
    "спельчук а": "ФОП №6 Спельчук А.А.",
    "8": "ФОП №8 Чолан Л.",
    "Чолан": "ФОП №8 Чолан Л.",
}

# ---------------------------
# 🔹 Стани
# ---------------------------
WAITING_REPORT_PERIOD, WAITING_REPORT_OWNER, WAITING_REPORT_FOP = range(3)
WAITING_EXPENSE_TYPE, WAITING_EXPENSE_INPUT = range(3, 5)
WAITING_PERIOD, WAITING_LOCATION, WAITING_CHANGE, WAITING_CATEGORY, WAITING_SUBCATEGORY = range(5, 10)
WAITING_SUBSUBCATEGORY = 10  # ← НОВИЙ стан для третього рівня
WAITING_EXPENSE_DATE = 901
WAITING_MANUAL_DATE = 902

async def ask_expense_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Сьогодні", callback_data="date_today")],
        [InlineKeyboardButton("📆 Вчора", callback_data="date_yesterday")],
        [InlineKeyboardButton("✏️ Ввести дату вручну", callback_data="date_manual")]
    ]
    await update.callback_query.message.reply_text(
        "📆 Оберіть дату операції:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_EXPENSE_DATE

def parse_amount(value):
    """
    Універсальний парсер чисел із Google Sheets:
    - '80,00' → 80.0
    - '2 000,00' → 2000.0
    - '21 876,38' → 21876.38
    - '75 000,00 грн.' → 75000.0
    - '80, 600' → 80600.0
    """
    if value is None or str(value).strip() == '':
        return 0.0

    text = str(value).strip()

    # 1️⃣ Нормалізуємо Unicode (прибирає різні види пробілів)
    text = unicodedata.normalize("NFKC", text)

    # 2️⃣ Видаляємо все зайве: 'грн', пробіли, табуляцію, валюту
    text = re.sub(r"[^\d,.\-]", "", text)

    # 3️⃣ Прибираємо нерозривні / тонкі / звичайні пробіли між цифрами
    text = text.replace(" ", "").replace("\u00A0", "").replace(" ", "")

    # 4️⃣ Якщо є і крапка, і кома
    if "," in text and "." in text:
        # Визначаємо формат
        if text.rfind(",") > text.rfind("."):
            # Європейський формат: 1.250,50 → 1250.50
            text = text.replace(".", "").replace(",", ".")
        else:
            # Англійський: 1,250.50 → 1250.50
            text = text.replace(",", "")
    else:
        # Якщо тільки кома — міняємо на крапку
        text = text.replace(",", ".")

    # 5️⃣ Якщо багато крапок — лишаємо останню (десяткову)
    parts = text.split(".")
    if len(parts) > 2:
        text = "".join(parts[:-1]) + "." + parts[-1]

    # 6️⃣ Конвертація
    try:
        return float(text)
    except ValueError:
        print(f"⚠️ parse_amount fail: {repr(value)} → {repr(text)}")
        return 0.0
    

async def handle_expense_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "date_today":
        selected_date = datetime.datetime.now().strftime("%d.%m.%Y")
    elif query.data == "date_yesterday":
        selected_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
    elif query.data == "date_manual":
        await query.message.reply_text("📝 Введіть дату у форматі ДД.ММ.РРРР (наприклад, 27.10.2025):")
        return WAITING_MANUAL_DATE
    else:
        return

    # Після вибору готової дати переходимо до вибору типу витрати
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


async def show_expense_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, selected_date: str):
    context.user_data["selected_date"] = selected_date

    keyboard = [
        [InlineKeyboardButton("💰 Dividends", callback_data="expense_type_dividends")],
        [InlineKeyboardButton("📈 Other Expenses", callback_data="expense_type_other")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
    ]

    if update.callback_query:
        await update.callback_query.message.reply_text(
            f"📅 Обрана дата: {selected_date}\n\nОбери тип:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            f"📅 Обрана дата: {selected_date}\n\nОбери тип:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    return WAITING_EXPENSE_TYPE

    
# ---------------------------
# 🔹 Парсер для dividends
# ---------------------------
def parse_expense(text: str):
    text = text.strip()
    pattern = r"^(ФОП|ГОТІВКА)\s+(.+?)\s+([А-ЯІЇЄҐ][а-яіїєґ]+(?:\s+[А-ЯІЇЄҐ][а-яіїєґ]+)?)?\s+(.+?)?\s+(\d+(?:[ ,]\d{3})*(?:\.\d+)?)\s*(.*)$"
    match = re.match(pattern, text, re.IGNORECASE | re.UNICODE)
    if not match:
        return None

    prefix, source_str, owner, category, amount_str, note = match.groups()
    owner = owner.strip() if owner else ''
    category = category.strip() if category else ''
    try:
        amount = float(amount_str.replace(',', '').replace(' ', ''))
    except ValueError:
        return None

    if amount <= 0:
        return None

    if prefix.upper() == "ФОП":
        possible_source = source_str.lower().strip()
        matched_key = next((k for k in ACCOUNT_MAP if k in possible_source), None)
        source = ACCOUNT_MAP.get(matched_key, source_str.strip()) if matched_key else source_str.strip()
    else:
        source = "Готівка"

    return {
        "джерело": source,
        "власник": owner,
        "категорія": category,
        "сума": amount,
        "примітка": note.strip() if note.strip() else None
    }

# ---------------------------
# 🔹 Простий парсер для 'other'
# ---------------------------
def parse_expense_simple(text: str):
    text = text.strip()
    pattern = r"^(ФОП|ГОТІВКА)\s+(.+?)\s+(\d+(?:[ ,]\d{3})*(?:\.\d+)?)\s*(.*)$"
    match = re.match(pattern, text, re.IGNORECASE | re.UNICODE)
    if not match:
        return None

    prefix, source_str, amount_str, note = match.groups()
    try:
        amount = float(amount_str.replace(',', '').replace(' ', ''))
    except ValueError:
        return None

    if amount <= 0:
        return None

    if prefix.upper() == "ФОП":
        possible_source = source_str.lower().strip()
        matched_key = next((k for k in ACCOUNT_MAP if k in possible_source), None)
        source = ACCOUNT_MAP.get(matched_key, source_str.strip()) if matched_key else source_str.strip()
    else:
        source = "Готівка"

    return {
        "рахунок": source,
        "сума": amount,
        "коментар": note.strip() if note.strip() else None
    }

# ---------------------------
# 🔹 Додавання (фікс: сума як число, дата як string для Sheets)
# ---------------------------
def add_expense_to_sheet(parsed: dict, context_data: dict, expense_type: str):
    sheet = get_sheet_by_type(expense_type)
    try:
        now = datetime.datetime.now()
        # ✅ Використовуємо дату користувача, якщо задана
        date_str = context_data.get("selected_date", datetime.datetime.now().strftime("%d.%m.%Y"))

        subcategory = context_data.get('subcategory', '')
        subsubcategory = context_data.get('subsubcategory', '')

        if expense_type == 'dividends':
            date_with_time = now.strftime("%d.%m.%Y %H:%M")
            row = [
                date_with_time,
                parsed["джерело"],
                parsed["власник"],
                parsed["категорія"],
                parsed["сума"],
                parsed["примітка"] or ""
            ]
            sheet.append_row(row, value_input_option='USER_ENTERED')
        else:
            period = context_data.get('period', "Літо 2025")
            location = context_data.get('location', "Операційні витрати на всі локації")
            change = context_data.get('change', '')
            category = context_data.get('category', '')
            subcategory = context_data.get('subcategory', '')
            category_vitrat = ''

            row = [
                date_str,  # ✅ тут уже правильна дата
                "Розхід",
                parsed["рахунок"],
                period,
                location,
                category_vitrat,
                change,
                category,
                subcategory,
                subsubcategory,
                parsed["сума"],
                parsed["коментар"] or ""
            ]
            sheet.append_row(row, value_input_option='USER_ENTERED')

        logging.info(f"Додано в '{sheet.title}': {subcategory} {subsubcategory} {parsed['сума']} грн ({date_str})")
    except Exception as e:
        logging.error(f"Помилка: {e}")
        raise e


# ---------------------------
# 🔹 Звіт
# ---------------------------


from collections import defaultdict
import logging

def generate_camp_summary(camp_name: str, detailed: bool = True):
    try:
        camp_lower = camp_name.strip().lower()
        income_total = 0.0
        expense_total = 0.0
        income_count = 0
        expense_count = 0

        sheet = SHEET_MAP['other']
        rows = sheet.get_all_records(expected_headers=OTHER_HEADERS)
        logging.info(f"Завантажено {len(rows)} рядків для '{camp_name}'")

        location_groups = defaultdict(float) if detailed else None
        income_category_groups = defaultdict(float) if detailed else None
        expense_category_groups = defaultdict(float) if detailed else None

        for row in rows:
            period = str(row.get("Період", "")).strip().lower()
            type_ = str(row.get("Група", "")).strip().lower()
            location = str(row.get("Локація", "Невідомо")).strip()
            category_raw = str(row.get("Категорії", "")).strip()

            if period == camp_lower:
                raw_sum = row.get("Сума", "")
                amount = parse_amount(raw_sum)
                if amount > 0:  # Ігнор blanks/0
                    # Fallback для категорій
                    category = category_raw
                    if not category:
                        if "дохід" in type_:
                            category = str(row.get("Дод. категорії", row.get("Зміни", "Дод. дохід"))).strip()
                        else:
                            category = str(row.get("Дод. категорії", row.get("Зміни", "Дод. витрати"))).strip()

                    if "дохід" in type_:
                        income_total += amount
                        income_count += 1
                        if detailed and income_category_groups:
                            income_category_groups[category] += amount
                    elif "розхід" in type_:
                        expense_total += amount
                        expense_count += 1
                        if detailed:
                            location_groups[location] += amount
                            expense_category_groups[category] += amount

                            # Дебаг для малих сум (тимчасово)
                            if amount < 1000:
                                logging.warning(f"DEBUG ROW: Дата={row.get('Дата')}, raw={repr(raw_sum)}, parsed={amount}, loc={location}, cat={category}")

        balance = income_total - expense_total
        expense_percent = (expense_total / income_total * 100) if income_total > 0 else 0

        report_lines = [
            f"🏕️ *Фінансовий звіт по табору: {camp_name}*\n",
            f"──────────────\n",
            f"🟢 Дохід: {income_total:,.2f} грн ({income_count} записів)\n",
            f"🔴 Розхід: {expense_total:,.2f} грн ({expense_count} записів, {expense_percent:.1f}% від доходу)\n",
            f"⚖️ Різниця: {balance:,.2f} грн"
        ]

        if detailed:
            # По локаціях (розхід)
            if location_groups:
                report_lines.append("\n📍 Розхід по локаціях:")
                for loc, amt in sorted(location_groups.items(), key=lambda x: x[1], reverse=True):
                    pct = (amt / expense_total * 100) if expense_total > 0 else 0
                    report_lines.append(f"  • {loc}: {amt:,.2f} грн ({pct:.1f}%)")

            # По категоріях доходу
            if income_category_groups:
                total_inc_cat = sum(income_category_groups.values())
                if total_inc_cat > 0:
                    report_lines.append("\n🟢 Дохід по категоріях:")
                    for cat, amt in sorted(income_category_groups.items(), key=lambda x: x[1], reverse=True):
                        if amt > 0:
                            pct = (amt / total_inc_cat * 100)
                            report_lines.append(f"  • {cat}: {amt:,.2f} грн ({pct:.1f}%)")

            # По категоріях розходу
            if expense_category_groups:
                report_lines.append("\n📊 Розхід по категоріях витрат:")
                for cat, amt in sorted(expense_category_groups.items(), key=lambda x: x[1], reverse=True):
                    if amt > 0:
                        pct = (amt / expense_total * 100) if expense_total > 0 else 0
                        report_lines.append(f"  • {cat}: {amt:,.2f} грн ({pct:.1f}%)")

        report = "\n".join(report_lines)
        logging.info(f"Звіт '{camp_name}': дохід={income_total} ({income_count}), розхід={expense_total} ({expense_count})")
        return report, 'Markdown'

    except Exception as e:
        logging.exception("Помилка у generate_camp_summary")
        return f"❌ Помилка: {e}", None



def generate_report(date_range=None, owner=None, fop=None, expense_type='dividends'):
    sheet = get_sheet_by_type(expense_type)
    headers = DIV_HEADERS if expense_type == 'dividends' else OTHER_HEADERS
    try:
        rows = sheet.get_all_records(expected_headers=headers)
        logging.info(f"Завантажено {len(rows)} з '{sheet.title}'")
    except Exception as e:
        return f"❌ Помилка: {e}"

    if not rows:
        return "📭 Порожньо."

    filtered = rows[:]

    if date_range:
        start_str, end_str = date_range.split("-")
        start = datetime.datetime.strptime(start_str, "%d.%m.%Y")
        end = datetime.datetime.strptime(end_str, "%d.%m.%Y")
        filtered = []
        for row in rows:
            try:
                row_date_str = row.get("Дата", "")
                if " " in row_date_str:
                    row_date = datetime.datetime.strptime(row_date_str, "%Y-%m-%d %H:%M")
                else:
                    row_date = datetime.datetime.strptime(row_date_str, "%Y-%m-%d")
                if start.date() <= row_date.date() <= end.date():
                    filtered.append(row)
            except ValueError:
                continue

    if owner and expense_type == 'dividends':
        filtered = [r for r in filtered if r.get("Власник", "").strip().lower() == owner.lower()]
    elif owner and expense_type == 'other':
        filtered = [r for r in filtered if owner.lower() in r.get("Коментар", "").lower()]

    if fop:
        col = "Джерело" if expense_type == 'dividends' else "Рахунок"
        filtered = [r for r in filtered if r.get(col, "").strip() == fop]

    if not filtered:
        return "⚠️ Немає даних."

    totals_by_category = {}
    for row in filtered:
        if expense_type == 'dividends':
            category = row.get("Категорія", "Невідомо")
            sum_raw = str(row.get("Сума", "0"))
        else:
            category = row.get("Дод. категорії", "Невідомо")
            sum_raw = str(row.get("Сума", "0"))

        # Очищення для звіту (якщо є форматування)
        sum_clean = re.sub(r'[ ,грн грн\. ]', '', sum_raw, flags=re.IGNORECASE).strip()
        try:
            amount = parse_amount(row['Сума'])
        except ValueError:
            amount = 0.0
        totals_by_category[category] = totals_by_category.get(category, 0) + amount

    report_lines = [f"📊 Звіт з '{sheet.title}'"]
    if date_range:
        report_lines.append(f"🗓️ Період: {date_range}")
    if owner:
        report_lines.append(f"👤 {owner}")
    if fop:
        report_lines.append(f"💼 {fop}")
    report_lines.append("──────────────")

    total_sum = sum(totals_by_category.values())
    for cat, amount in sorted(totals_by_category.items(), key=lambda x: x[1], reverse=True):
        report_lines.append(f"📂 {cat}: {amount:.2f} грн")

    report_lines.append(f"──────────────\n💰 Всього: {total_sum:.2f} грн")
    return "\n".join(report_lines)

def generate_daily_report(expense_type=None):  # expense_type=None для всіх типів
    today = datetime.date.today().strftime("%Y-%m-%d")
    report_lines = [f"📅 *Звіт за день: {today}*"]
    
    # Оброби обидва аркуші, якщо expense_type=None
    sheets_data = {}
    for etype, sheet in SHEET_MAP.items():
        if expense_type and etype != expense_type:
            continue
        try:
            headers = DIV_HEADERS if etype == 'dividends' else OTHER_HEADERS
            rows = sheet.get_all_records(expected_headers=headers)
            # Фільтр по сьогоднішній даті
            today_rows = []
            for row in rows:
                row_date_str = row.get("Дата", "")
                if row_date_str.startswith(today):  # Початок рядка = сьогодні
                    today_rows.append(row)
            sheets_data[etype] = today_rows
        except Exception as e:
            logging.error(f"Помилка для {etype}: {e}")
            continue
    
    if not any(sheets_data.values()):
        return report_lines[0] + "\n📭 Немає витрат за день."
    
    # Групування: {fop: {type: {'sum': float, 'count': int}}}
    totals = defaultdict(lambda: defaultdict(lambda: {'sum': 0.0, 'count': 0}))
    
    for etype, rows in sheets_data.items():
        col_fop = "Джерело" if etype == 'dividends' else "Рахунок"
        col_sum = "Сума"
        for row in rows:
            fop = row.get(col_fop, "Невідомо").strip()
            sum_raw = str(row.get(col_sum, "0"))
            sum_clean = re.sub(r'[ ,грн грн\. ]', '', sum_raw, flags=re.IGNORECASE).strip()
            try:
                amount = parse_amount(row['Сума'])
            except ValueError:
                amount = 0.0
            totals[fop][etype]['sum'] += amount
            totals[fop][etype]['count'] += 1
    
    report_lines.append("──────────────")
    grand_total = 0
    for fop, types in sorted(totals.items()):
        report_lines.append(f"💼 *{fop}*:")
        fop_total = 0
        for ttype, data in types.items():
            count = data['count']
            sum_ = data['sum']
            report_lines.append(f"  {ttype.capitalize()}: {count} операцій, {sum_:.2f} грн")
            fop_total += sum_
            grand_total += sum_
        report_lines.append(f"  *Всього по ФОП: {fop_total:.2f} грн*")
    
    report_lines.append(f"──────────────\n💰 *Загалом: {grand_total:.2f} грн*")
    return "\n".join(report_lines), 'Markdown'  # parse_mode


# ---------------------------
# 🔹 Меню
# ---------------------------
async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text="🔹 Оберіть дію нижче:"):
    keyboard = [
        [InlineKeyboardButton("➕ Додати витрату", callback_data="add_expense")],
        [InlineKeyboardButton("📊 Звіти", callback_data="reports_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)
    

# ---------------------------
# 🔹 Команди
# ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_main_menu(update, context, "👋 Привіт! тут ти можеш додати витрати до системи")

# ---------------------------
# 🔹 Обробка кнопок
# ---------------------------
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if 'nav_stack' not in context.user_data:
        context.user_data['nav_stack'] = []  # Стек кроків: ['period', 'location', 'change', 'category']

    if query.data == "add_expense":
        user_id = query.from_user.id
        if user_id in USER_ROLES:
            return await simplified_expense_flow(update, context, user_id)
        else:
            return await ask_expense_date(update, context)


    # --- 🆕 1. Запуск процесу додавання витрати — спочатку питаємо дату --- #
    if query.data == "add_expense":
        context.user_data['nav_stack'] = []  # Очистити стек на старті
        context.user_data.pop('is_transfer', None)  # Очистити флаг
        return await ask_expense_date(update, context)
    # ---------------------------------------------------------------------- #

    # --- 🆕 2. Після вибору дати користувач потрапляє сюди (через proceed_to_expense_input) --- #
    elif query.data.startswith("expense_date_done_"):
        selected_date = query.data.replace("expense_date_done_", "")
        context.user_data["selected_date"] = selected_date

        # Тепер показуємо вибір типу витрати
        keyboard = [
            [InlineKeyboardButton("💰 Dividends", callback_data="expense_type_dividends")],
            [InlineKeyboardButton("📈 Other Expenses", callback_data="expense_type_other")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
        ]
        await query.message.reply_text(f"📅 Обрана дата: {selected_date}\n\nОбери тип:", reply_markup=InlineKeyboardMarkup(keyboard))
        return WAITING_EXPENSE_TYPE
    # ---------------------------------------------------------------------- #

    elif query.data.startswith("expense_type_"):
        expense_type = query.data.split("_")[-1]
        context.user_data['expense_type'] = expense_type
        if expense_type == 'dividends':
            prompt = "Введи: ФОП радул Ваня Мантра 3600 ЗП"
            await query.message.reply_text(f"Тип: {expense_type}\n{prompt}")
            return WAITING_EXPENSE_INPUT
        else:
            context.user_data['nav_stack'].append('type')  # Додай крок
            keyboard = [
                [InlineKeyboardButton("☀️ Літо 2025", callback_data="per_lito_2025")],
                [InlineKeyboardButton("🍂 Осінь 2025", callback_data="per_osin_2025")],
                [InlineKeyboardButton("❄️ Зима 2026", callback_data="per_zima_2026")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
            ]
            await query.message.reply_text("Обери Період:", reply_markup=InlineKeyboardMarkup(keyboard))
            return WAITING_PERIOD


    elif query.data.startswith("per_"):
        per_key = query.data.split("_", 1)[-1]  # Фікс: split("_", 1) для "per_lito_2025" → 'lito_2025'
        context.user_data['period'] = CONFIG_OTHER['periods'][per_key]
        context.user_data['nav_stack'].append('period')  # Додай крок
        
        # Динамічні локації за періодом
        relevant_locs = CONFIG_OTHER.get('locations_by_period', {}).get(per_key, ['all'])
        keyboard = [
            [InlineKeyboardButton(CONFIG_OTHER['locations'][loc_key], callback_data=f"loc_{loc_key}")] 
            for loc_key in relevant_locs
        ]
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
        
        await query.message.reply_text(
            f"Період: {context.user_data['period']}\nОбери Локацію (релевантні для періоду):", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return WAITING_LOCATION

    elif query.data.startswith("loc_"):
        loc_key = query.data.split("_", 1)[-1]
        context.user_data['location'] = CONFIG_OTHER['locations'][loc_key]
        context.user_data['nav_stack'].append('location')  # Додай крок
        
        if loc_key == 'Transfer':
            # Спеціальна логіка для Трансферу: пропустити "Зміну", перейти до Категорій
            context.user_data['is_transfer'] = True
            context.user_data['change'] = 'Трансфер'  # Для збереження в аркуші (опціонально)
            
            transfer_categories = list(CONFIG_OTHER['categories_by_location']['Transfer'].keys())
            ascii_cats = [CAT_UKR_TO_ASCII.get(cat, cat.lower().replace(' ', '_')) for cat in transfer_categories]
            keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat_{ascii_cat}")] for cat, ascii_cat in zip(transfer_categories, ascii_cats)]
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
            
            await query.message.reply_text(
                f"Локація: {context.user_data['location']}\nОбери Категорію:", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            context.user_data['nav_stack'].append('category')  # Додай 'category' напряму
            return WAITING_CATEGORY
        else:
            # Стандартна логіка для інших локацій: Динамічні зміни з per-period фоллбеком
            per_key = next((k for k, v in CONFIG_OTHER['periods'].items() if v == context.user_data.get('period')), None)
            changes_config = CONFIG_OTHER.get('changes_by_location_period', {}).get(per_key, {})
            relevant_changes = changes_config.get(loc_key, CONFIG_OTHER.get('changes_by_location', {}).get(loc_key, list(CHANGE_ASCII_TO_UKR.keys())))
            keyboard = [
                [InlineKeyboardButton(CHANGE_ASCII_TO_UKR[suffix], callback_data=f"change_{suffix}")] 
                for suffix in relevant_changes
            ]
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
            
            await query.message.reply_text(
                f"Локація: {context.user_data['location']}\nОбери Зміну (релевантні для локації):", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return WAITING_CHANGE

    elif query.data.startswith("change_"):
        suffix = query.data.split("_", 1)[-1]
        change = CHANGE_ASCII_TO_UKR[suffix]
        context.user_data['change'] = change
        context.user_data['nav_stack'].append('change')  # Додай крок
        
        categories = CONFIG_OTHER['categories_by_change'].get(change.lower(), ['Маркетинг'])
        ascii_cats = [CAT_UKR_TO_ASCII.get(cat, cat.lower().replace(' ', '_')) for cat in categories]
        keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat_{ascii_cat}")] for cat, ascii_cat in zip(categories, ascii_cats)]
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
        await query.message.reply_text(f"Зміна: {change}\nОбери Категорію:", reply_markup=InlineKeyboardMarkup(keyboard))
        return WAITING_CATEGORY

    elif query.data.startswith("cat_"):
        ascii_cat = query.data.split("_", 1)[-1]
        cat = CAT_ASCII_TO_UKR.get(ascii_cat, ascii_cat.replace('_', ' ').title())  # Fallback для безпеки
        context.user_data['category'] = cat
        context.user_data['nav_stack'].append('category')  # Додай крок
        
        # Визначення підкатегорій: стандартні або для Трансферу
        # Фікс: нормалізуємо cat до lowercase для пошуку в dict
        cat_lower = cat.lower()
        subcats = CONFIG_OTHER['subcategories_by_category'].get(cat_lower, [])
        if context.user_data.get('is_transfer'):
            subcats = CONFIG_OTHER['categories_by_location']['Transfer'].get(cat, [])
        
        if not subcats:
            # Без підкатегорій: напряму до введення
            await query.message.reply_text(
                f"Категорія: {cat}\n"
                f"Зміни: {CONFIG_OTHER['changes_by_subcategory'].get(cat, 'Стандартні')}\n"
                "Введи рахунок/суму/коментар: ФОП 2 20000 реклама"
            )
            context.user_data['subcategory'] = ''  # Порожня
            return WAITING_EXPENSE_INPUT
        else:
            # Показати підкатегорії
            ascii_subcats = [SUB_UKR_TO_ASCII.get(sub, sub.lower().replace(' ', '_')) for sub in subcats]
            keyboard = [[InlineKeyboardButton(sub, callback_data=f"sub_{ascii_sub}")] for sub, ascii_sub in zip(subcats, ascii_subcats)]
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
            await query.message.reply_text(f"Категорія: {cat}\nОбери Підкатегорію:", reply_markup=InlineKeyboardMarkup(keyboard))
            return WAITING_SUBCATEGORY

    elif query.data.startswith("sub_"):
        ascii_sub = query.data.split("_", 1)[-1]
        sub = SUB_ASCII_TO_UKR.get(ascii_sub, ascii_sub.replace('_', ' ').title())  # Fallback
        context.user_data['subcategory'] = sub
        context.user_data['nav_stack'].append('subcategory')  # Додай крок
        
        # ← НОВА ЛОГІКА: Перевіряємо наявність суб-підкатегорій
        sub_lower = sub.lower()
        subsubs = CONFIG_OTHER.get('subsubcategories_by_subcategory', {}).get(sub_lower, [])
        
        if subsubs:
            # Якщо є суб-підкатегорії, показуємо їх
            ascii_subsubs = [SUBSUB_UKR_TO_ASCII.get(s, s.lower().replace(' ', '_')) for s in subsubs]
            keyboard = [[InlineKeyboardButton(s, callback_data=f"subsub_{ascii_s}")] for s, ascii_s in zip(subsubs, ascii_subsubs)]
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
            await query.message.reply_text(
                f"Підкатегорія: {sub}\nОбери суб-підкатегорію:", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            context.user_data['nav_stack'].append('subsubcategory')  # Додай крок
            return WAITING_SUBSUBCATEGORY
        else:
            # Без суб-підкатегорій: напряму до введення
            await query.message.reply_text(
                f"Підкатегорія: {sub}\n"
                f"Зміни: {CONFIG_OTHER['changes_by_subcategory'].get(sub, 'Стандартні')}\n"
                "Введи рахунок/суму/коментар: ФОП 2 20000 реклама"
            )
            context.user_data['subsubcategory'] = ''  # Порожня
            return WAITING_EXPENSE_INPUT

    elif query.data.startswith("subsub_"):  # ← НОВИЙ обробник для третього рівня
        ascii_subsub = query.data.split("_", 2)[-1]  # "subsub_yana" → "yana"
        subsub = SUBSUB_ASCII_TO_UKR.get(ascii_subsub, ascii_subsub.replace('_', ' ').title())  # Fallback
        context.user_data['subsubcategory'] = subsub
        context.user_data['nav_stack'].append('subsubcategory')  # Додай крок (хоча йдемо до input)
        
        sub = context.user_data.get('subcategory', '')
        await query.message.reply_text(
            f"Суб-підкатегорія: {subsub} (під {sub})\n"
            f"Зміни: {CONFIG_OTHER['changes_by_subcategory'].get(sub, 'Стандартні')}\n"
            "Введи рахунок/суму/коментар: ФОП 2 20000 реклама"
        )
        return WAITING_EXPENSE_INPUT

    # ← НОВИЙ: Логіка для "back" (крок назад)
    elif query.data == "back":
        if not context.user_data['nav_stack']:
            await send_main_menu(update, context)  # Якщо стек порожній — на головне
            return ConversationHandler.END
        
        prev_step = context.user_data['nav_stack'].pop()  # Поп з стеку
        
        # Генеруй клавіатуру залежно від prev_step
        if prev_step == 'type':
            # Назад до вибору типу
            keyboard = [
                [InlineKeyboardButton("💰 Dividends", callback_data="expense_type_dividends")],
                [InlineKeyboardButton("📈 Other Expenses", callback_data="expense_type_other")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
            ]
            await query.message.reply_text("Обери тип:", reply_markup=InlineKeyboardMarkup(keyboard))
            return WAITING_EXPENSE_TYPE
        elif prev_step == 'period':
            # Назад до вибору періоду
            keyboard = [
                [InlineKeyboardButton("☀️ Літо 2025", callback_data="per_lito_2025")],
                [InlineKeyboardButton("🍂 Осінь 2025", callback_data="per_osin_2025")],
                [InlineKeyboardButton("❄️ Зима 2026", callback_data="per_zima_2026")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
            ]
            await query.message.reply_text("Обери Період:", reply_markup=InlineKeyboardMarkup(keyboard))
            return WAITING_PERIOD
        elif prev_step == 'location':
            # Назад до вибору локації (з поточним періодом)
            per_key = next((k for k, v in CONFIG_OTHER['periods'].items() if v == context.user_data.get('period')), 'lito_2025')
            relevant_locs = CONFIG_OTHER.get('locations_by_period', {}).get(per_key, ['all'])
            keyboard = [
                [InlineKeyboardButton(CONFIG_OTHER['locations'][loc_key], callback_data=f"loc_{loc_key}")] 
                for loc_key in relevant_locs
            ]
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
            await query.message.reply_text(
                f"Період: {context.user_data.get('period', 'Не вказано')}\nОбери Локацію:", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return WAITING_LOCATION
        elif prev_step == 'change':
            # Назад до вибору зміни (з поточною локацією)
            loc_key = next((k for k, v in CONFIG_OTHER['locations'].items() if v == context.user_data.get('location')), 'all')
            per_key = next((k for k, v in CONFIG_OTHER['periods'].items() if v == context.user_data.get('period')), None)
            changes_config = CONFIG_OTHER.get('changes_by_location_period', {}).get(per_key, {})
            relevant_changes = changes_config.get(loc_key, CONFIG_OTHER.get('changes_by_location', {}).get(loc_key, list(CHANGE_ASCII_TO_UKR.keys())))
            keyboard = [
                [InlineKeyboardButton(CHANGE_ASCII_TO_UKR[suffix], callback_data=f"change_{suffix}")] 
                for suffix in relevant_changes
            ]
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
            await query.message.reply_text(
                f"Локація: {context.user_data.get('location', 'Не вказано')}\nОбери Зміну:", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return WAITING_CHANGE
        elif prev_step == 'category':
            # Назад до вибору категорії (з поточною зміною) або локації для Трансферу
            if context.user_data.get('is_transfer'):
                # Для Трансферу: назад до локації (без зміни)
                per_key = next((k for k, v in CONFIG_OTHER['periods'].items() if v == context.user_data.get('period')), 'lito_2025')
                relevant_locs = CONFIG_OTHER.get('locations_by_period', {}).get(per_key, ['all'])
                keyboard = [
                    [InlineKeyboardButton(CONFIG_OTHER['locations'][loc_key], callback_data=f"loc_{loc_key}")] 
                    for loc_key in relevant_locs
                ]
                keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
                await query.message.reply_text(
                    f"Період: {context.user_data.get('period', 'Не вказано')}\nОбери Локацію:", 
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return WAITING_LOCATION
            else:
                # Стандартно: назад до зміни
                loc_key = next((k for k, v in CONFIG_OTHER['locations'].items() if v == context.user_data.get('location')), 'all')
                per_key = next((k for k, v in CONFIG_OTHER['periods'].items() if v == context.user_data.get('period')), None)
                changes_config = CONFIG_OTHER.get('changes_by_location_period', {}).get(per_key, {})
                relevant_changes = changes_config.get(loc_key, CONFIG_OTHER.get('changes_by_location', {}).get(loc_key, list(CHANGE_ASCII_TO_UKR.keys())))
                keyboard = [
                    [InlineKeyboardButton(CHANGE_ASCII_TO_UKR[suffix], callback_data=f"change_{suffix}")] 
                    for suffix in relevant_changes
                ]
                keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
                await query.message.reply_text(
                    f"Локація: {context.user_data.get('location', 'Не вказано')}\nОбери Зміну:", 
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return WAITING_CHANGE
        elif prev_step == 'subcategory':
            # Назад до вибору підкатегорії (з поточною категорією)
            cat = context.user_data.get('category', '')
            # Визначення підкатегорій (з урахуванням Трансферу)
            cat_lower = cat.lower()
            subcats = CONFIG_OTHER['subcategories_by_category'].get(cat_lower, [])
            if context.user_data.get('is_transfer'):
                subcats = CONFIG_OTHER['categories_by_location']['Transfer'].get(cat, [])
            ascii_subcats = [SUB_UKR_TO_ASCII.get(sub, sub.lower().replace(' ', '_')) for sub in subcats]
            keyboard = [[InlineKeyboardButton(sub, callback_data=f"sub_{ascii_sub}")] for sub, ascii_sub in zip(subcats, ascii_subcats)]
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
            await query.message.reply_text(f"Категорія: {cat}\nОбери Підкатегорію:", reply_markup=InlineKeyboardMarkup(keyboard))
            return WAITING_SUBCATEGORY
        elif prev_step == 'subsubcategory':  # ← НОВИЙ: Назад до підкатегорії
            # Назад до вибору підкатегорії (з поточною категорією)
            cat = context.user_data.get('category', '')
            cat_lower = cat.lower()
            subcats = CONFIG_OTHER['subcategories_by_category'].get(cat_lower, [])
            if context.user_data.get('is_transfer'):
                subcats = CONFIG_OTHER['categories_by_location']['Transfer'].get(cat, [])
            ascii_subcats = [SUB_UKR_TO_ASCII.get(sub, sub.lower().replace(' ', '_')) for sub in subcats]
            keyboard = [[InlineKeyboardButton(sub, callback_data=f"sub_{ascii_sub}")] for sub, ascii_sub in zip(subcats, ascii_subcats)]
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
            await query.message.reply_text(f"Категорія: {cat}\nОбери Підкатегорію:", reply_markup=InlineKeyboardMarkup(keyboard))
            return WAITING_SUBCATEGORY
        
        elif query.data == "reports_div":
            context.user_data['report_type'] = 'dividends'
            await query.message.reply_text("Введи ім’я власника для звіту:")
            return WAITING_REPORT_OWNER

        elif query.data == "reports_other":
            context.user_data['report_type'] = 'other'
            await query.message.reply_text("Введи ФОП або ключове слово для звіту:")
            return WAITING_REPORT_FOP

    
    elif query.data == "daily_report":
        report_text, parse_mode = generate_daily_report()  # Всі типи
        await query.message.reply_text(report_text, parse_mode=parse_mode)
        await send_main_menu(update, context)

    # ... решта коду без змін (reports_menu, back_main тощо)
    elif query.data == "back_main":
        context.user_data.clear()  # Очистити все, включаючи стек та флаги
        await send_main_menu(update, context)

    elif query.data == "reports_menu":
        keyboard = [
            [InlineKeyboardButton("📊 Dividends звіти", callback_data="reports_div")],
            [InlineKeyboardButton("📊 Other звіти", callback_data="reports_other")],
            [InlineKeyboardButton("📅 Звіт за день", callback_data="daily_report")],  # ← НОВЕ
            [InlineKeyboardButton("🏕️ Звіт по табору", callback_data="camp_summary_menu")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
        ]
        await query.message.reply_text("Обери аркуш для звіту:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "camp_summary_menu":
        keyboard = [
            [InlineKeyboardButton("☀️ Літо 2025", callback_data="camp_summary_lito_2025")],
            [InlineKeyboardButton("🍂 Осінь 2025", callback_data="camp_summary_osin_2025")],
            [InlineKeyboardButton("❄️ Зима 2026", callback_data="camp_summary_zima_2026")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="reports_menu")]
        ]
        await query.message.reply_text("Оберіть табір для звіту:", reply_markup=InlineKeyboardMarkup(keyboard))

    
    elif query.data.startswith("camp_summary_"):
        key = query.data.split("_", 2)[-1]  # lito_2025, osin_2025, zima_2026
        # Карта ключів -> назва табору (з конфігу)
        camp_map = CONFIG_OTHER['periods']
        camp_name = camp_map.get(key, key)
        report_text, parse_mode = generate_camp_summary(camp_name)
        await query.message.reply_text(report_text, parse_mode=parse_mode)
        await send_main_menu(update, context)
    

# ---------------------------
# 🔹 Функції для витрат
# ---------------------------
async def process_expense_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    expense_type = context.user_data.get('expense_type', 'dividends')
    if expense_type == 'dividends':
        parsed = parse_expense(text)
    else:
        parsed = parse_expense_simple(text)
    if parsed:
        try:
            add_expense_to_sheet(parsed, context.user_data, expense_type)
            subsub = context.user_data.get('subsubcategory', '')
            await update.message.reply_text(f"✅ Додано в {expense_type}!\nСума: {parsed['сума']} грн\n{subsub}" if subsub else f"✅ Додано в {expense_type}!\nСума: {parsed['сума']} грн")
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")
    else:
        await update.message.reply_text("⚠️ Не розпізнано. Спробуй ще.")
    context.user_data.clear()
    await send_main_menu(update, context)
    return ConversationHandler.END

# ---------------------------
# 🔹 Функції для звітів
# ---------------------------
async def process_report_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner = update.message.text.strip()
    report_type = context.user_data.get('report_type', 'dividends')
    if owner:
        report_text = generate_report(owner=owner, expense_type=report_type)
        await update.message.reply_text(report_text)
        context.user_data.pop('report_type', None)
    else:
        await update.message.reply_text("⚠️ Ім'я порожнє.")
        return WAITING_REPORT_OWNER
    await send_main_menu(update, context)
    return ConversationHandler.END

async def process_report_fop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fop = update.message.text.strip()
    report_type = context.user_data.get('report_type', 'dividends')
    if fop:
        report_text = generate_report(fop=fop, expense_type=report_type)
        await update.message.reply_text(report_text)
        context.user_data.pop('report_type', None)
    else:
        await update.message.reply_text("⚠️ Порожнє.")
        return WAITING_REPORT_FOP
    await send_main_menu(update, context)
    return ConversationHandler.END

# ---------------------------
# 🔹 Обробка повідомлень
# ---------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ Використовуй кнопки. /start")
    await send_main_menu(update, context)

# ---------------------------
# 🔹 Запуск
# ---------------------------
if __name__ == "__main__":
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не знайдено в .env!")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Conv для витрат
    expense_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_callback, pattern="^add_expense$")],
        states={
            WAITING_EXPENSE_TYPE: [CallbackQueryHandler(handle_callback, pattern="^expense_type_")],
            WAITING_PERIOD: [CallbackQueryHandler(handle_callback, pattern="^per_")],
            WAITING_LOCATION: [CallbackQueryHandler(handle_callback, pattern="^loc_")],
            WAITING_CHANGE: [CallbackQueryHandler(handle_callback, pattern="^change_")],
            WAITING_CATEGORY: [CallbackQueryHandler(handle_callback, pattern="^cat_")],
            WAITING_SUBCATEGORY: [CallbackQueryHandler(handle_callback, pattern="^sub_")],
            WAITING_SUBSUBCATEGORY: [CallbackQueryHandler(handle_callback, pattern="^subsub_")],  # ← НОВИЙ
            WAITING_EXPENSE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_expense_input)],
            WAITING_EXPENSE_DATE: [CallbackQueryHandler(handle_expense_date_selection)],
            WAITING_MANUAL_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_date_input)],

        },
        fallbacks=[CommandHandler('start', start), MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        per_chat=True,
        per_message=False,
    )
    app.add_handler(expense_conv)

    # Conv для звітів
    report_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_callback, pattern="^report_owner_"),
            CallbackQueryHandler(handle_callback, pattern="^report_fop_"),
        ],
        states={
            WAITING_REPORT_OWNER: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_report_owner)],
            WAITING_REPORT_FOP: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_report_fop)],
        },
        fallbacks=[CommandHandler('start', start), MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        per_chat=True,
        per_message=False,
    )
    app.add_handler(report_conv)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("✅ Бот запущено!")
    app.run_polling()