import os
import json
import logging
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()
logging.basicConfig(level=logging.INFO)

# --- Налаштування Google Sheets ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS = None # Ініціалізація змінної для облікових даних

# 1. Спроба завантажити з JSON-рядка (для Render/Хмарних сервісів)
if os.getenv("GOOGLE_CREDS"):
    try:
        # Використовуємо ключ із змінної середовища
        creds_dict = json.loads(os.getenv("GOOGLE_CREDS"))
        CREDS = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        logging.info("✅ Google Sheets: Авторизація через змінну GOOGLE_CREDS.")
    except Exception as e:
        logging.error(f"❌ Google Sheets: Помилка парсингу GOOGLE_CREDS. Перевірте формат JSON: {e}")

# 2. Спроба завантажити з локального файлу (ТІЛЬКИ для локального запуску)
elif os.path.exists('credentials.json'):
    try:
        CREDS = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', SCOPE)
        logging.info("✅ Google Sheets: Авторизація через локальний файл 'credentials.json'.")
    except Exception as e:
        logging.error(f"❌ Google Sheets: Помилка завантаження локального файлу: {e}")

# --- Ініціалізація клієнта та словника аркушів ---
GS_CLIENT = None
SHEET_MAP = {}

if CREDS:
    try:
        GS_CLIENT = gspread.authorize(CREDS)
        SHEET_BOOK = GS_CLIENT.open("WestCamp")
        
        # Словник аркушів
        SHEET_MAP = {
            'dividends': SHEET_BOOK.worksheet("Dividends"),
            'other': SHEET_BOOK.worksheet("ShiftExpenses"),
        }
        logging.info("✅ Google Sheets: З'єднання успішне.")
    except Exception as e:
        logging.error(f"❌ Google Sheets: Помилка відкриття таблиці 'WestCamp' або аркушів: {e}")
else:
    logging.error("❌ Google Sheets: Авторизація НЕ вдалася. Функції запису не працюватимуть.")


def get_sheet_by_type(expense_type: str):
    # Повертаємо аркуш, або None, якщо він не був ініціалізований
    if not SHEET_MAP:
        logging.warning("⚠️ SHEET_MAP не ініціалізовано. Функція запису не працює.")
        return None
    return SHEET_MAP.get(expense_type, SHEET_MAP.get('dividends'))

# Колонки
DIV_HEADERS = ['Дата', 'Джерело', 'Власник', 'Категорія', 'Сума', 'Примітка']
OTHER_HEADERS = [
    "Дата", "Група", "Рахунок", "Період", "Локація", "Категорія витрат",
    "Зміни", "Категорії", "Дод. категорії", "Дод. інформація", "Сума", "Коментар", "Факт / Прогноз"
]

# Конфіг для 'other'
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
    'categories_by_location': {
        'Transfer': {
            'Укрзалізниця': ['квитки', 'інші витрати'],
            'Автобуси': ['До локації', 'З локації', 'дод. витрати'],
            'Заробітна плата': ['Олександра', 'Ліза', 'інші'],
            'Дод. витрати': [],
        }
    },
    'changes': [
        "1 - Зміна", "2 - Зміна", "3 - Зміна", "4 - Зміна", "5 - Зміна",
        "6 - Зміна", "7 - Зміни", "Повернення авансів"
    ],
    'categories_by_change': {
        '1 - Зміна': ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору'],
        '2 - Зміна': ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору'],
        '3 - Зміна': ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору'],
        '4 - Зміна': ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору'],
        '5 - Зміна': ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору'],
        '6 - Зміна': ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору'],
        '7 - Зміни': ['Розваги', 'Команда', 'Проживання дітей', 'Додаткові витрати', 'Підготовка до табору'],
        'Операційні витрати': ['Маркетинг', 'Зарплата', 'Реклама'],
        'Повернення авансів': ['Повернення коштів', 'Аванс повернуто'],
    },
    'subcategories_by_category': {
        'rozvagy': ['Гонорар', 'Оплата дороги', 'Харчування', 'Автобуси', 'Дод. витрати', 'реквізит', 'музеї'],
        'komanda': ['Зарплата', 'Проживання і харчування', 'Трансфер команди', 'Дод. витрати'],
        'prozhivanie_ditey': ['За всю зміну', 'Дод. витрати'],
        'dodatkovi_vytraty': ['Канцтовари', 'Медикаменти', 'Паливо', 'Декор', 'Настілки', 'Інші витрати', 'Мерч'],
        'zarplata': ['Відділ продажів', 'Адмін', 'Директор', 'Маркетинг','Тех. працівники'],
        'logistyka': ['Транспорт', 'Склад'],
        'pover_koshtiv': ['Аванс 1', 'Аванс 2'],
        'zmina1': ['Деталь 1', 'Деталь 2'],
        'marketynh': ['Реклама', 'SMM', 'Промо', 'Креативи'],
    },
    'subsubcategories_by_category': {
        'viddil_prodazhiv': ['Яна', 'Віра', 'Соня'],
        'dyrektor': ['Олег', 'Леся'],
        'marketynh': ['Ярослав'],
        'tekh_pratsivnyky': ['Вова', 'Христина', 'інші'],
    },
    'changes_by_subcategory': {
        'reklama': "Рекламна кампанія",
        'dizayn': "Дизайн мерчу",
    }
}

# ASCII maps
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
    "Зміна 1": "zmina1", "Зміна 1a": "zmina1a", "Зміна 2": "zmina2", "Зміна 2b": "zmina2b",
    "Зміна до 7": "zmina_do7", "Зміна 7c": "zmina7c", "Розваги": "rozvagy", "Команда": "komanda",
    "Проживання дітей": "prozhivanie_ditey", "Додаткові витрати": "dodatkovi_vytraty",
    "Маркетинг": "marketynh", "Зарплата": "zarplata", "Логістика": "logistyka",
    "Повернення коштів": "pover_koshtiv", "Аванс повернуто": "avans_pover",
    "Укрзалізниця": "ukrzaliznytsia", "Автобуси": "avtobusy", "Заробітна плата": "zarobitna_plata",
    "Дод. витрати": "dod_vytraty", "Підготовка до табору": "pidhotovka_do_tabory"
}
CAT_ASCII_TO_UKR = {v: k for k, v in CAT_UKR_TO_ASCII.items()}

SUB_UKR_TO_ASCII = {
    "Реклама": "reklama", "Дизайн": "dizayn", "Відділ продажів": "vidpil_prodazhiv", "Адмін": "admin",
    "Транспорт": "transport", "Склад": "sklad", "Аванс 1": "avans1", "Аванс 2": "avans2",
    "Деталь 1": "detal1", "Деталь 2": "detal2", "Підготовка": "pidhotovka", "Зарплата": "zarplata",
    "Проживання і харчування": "prozhivanie_i_kharchuvannia", "Дод. витрати": "dod_vytraty",
    "Гонорар": "honorar", "Оплата дороги": "oplata_dorohy", "Харчування": "kharchuvannia",
    "Автобуси": "avtobusy", "реквізит": "rekvizyt", "музеї": "muzei", "Трансфер команди": "transfer_komandy",
    "За всю зміну": "za_vsyu_zminu", "Канцтовари": "kanctovary", "Медикаменти": "medykamenty",
    "Паливо": "palyvo", "Декор": "dekor", "Настілки": "nastilky", "Інші витрати": "inshi_vytraty",
    "Мерч": "merch", "квитки": "kvytky", "інші витрати": "inshi_vytraty", "До локації": "do_lokatsii",
    "З локації": "z_lokatsii", "дод. витрати": "dod_vytraty", "Олександра": "oleksandra",
    "Ліза": "liza", "інші": "inshi", "Директор": "dyrektor", "Тех. працівники": "tekh_pratsivnyky",
    "SMM": "smm", "Промо": "promo", "Креативи": "kreatyvy"
}
SUB_ASCII_TO_UKR = {v: k for k, v in SUB_UKR_TO_ASCII.items()}

SUBSUB_UKR_TO_ASCII = {
    "Яна": "yana", "Віра": "vira", "Соня": "sonya", "Олег": "oleg", "Леся": "lesya",
    "Вова": "vova", "Христина": "khrystyna", "інші": "inshi", "Ярослав": "yaroslav"
}
SUBSUB_ASCII_TO_UKR = {v: k for k, v in SUBSUB_UKR_TO_ASCII.items()}

# Словник ФОПів
ACCOUNT_MAP = {
    "радул і": "ФОП №1 Радул І.І.", "1": "ФОП №1 Радул І.І.", "радул я": "ФОП №2 Радул Я.Ю.",
    "2": "ФОП №2 Радул Я.Ю.", "скидан": "ФОП №3 Скидан Х.С.", "фоп скидан": "ФОП №3 Скидан Х.С.",
    "3": "ФОП №3 Скидан Х.С.", "фоп досієвич": "ФОП №4 Досієвич В.П.", "4": "ФОП №4 Досієвич В.П.",
    "фоп демедюк": "ФОП №5 Демедюк Л.В.", "5": "ФОП №5 Демедюк Л.В.", "фоп спельчук а": "ФОП №6 Спельчук А.А.",
    "6": "ФОП №6 Спельчук А.А.", "фоп спельчук о": "ФОП №7 Спельчук О.Ю.", "7": "ФОП №7 Спельчук О.Ю.",
    "радул": "ФОП №1 Радул І.І.", "досієвич": "ФОП №4 Досієвич В.П.", "демедюк": "ФОП №5 Демедюк Л.В.",
    "спельчук а": "ФОП №6 Спельчук А.А.", "8": "ФОП №8 Чолан Л.", "Чолан": "ФОП №8 Чолан Л.",
}

# Конфігурація для Dividends
DIVIDENDS_CONFIG = {
    'owners': {
        'vanya': 'Ваня',
        'yana': 'Яна'
    },
    'categories_by_owner': {
        'vanya': {
            'mantra': 'Мантра',
            'osobyste_vanya': 'Особисте Ваня',
            'synychka_vanya': 'Синичка Ваня',
            'novi_proekty_vanya': 'Нові проекти Ваня'
        },
        'yana': {
            'osobyste_yana': 'Особисте Яна',
            'synychka_yana': 'Синичка Яна',
            'novi_proekty_yana': 'Нові проекти Яна'
        }
    }
}

# Стани
WAITING_REPORT_PERIOD, WAITING_REPORT_OWNER, WAITING_REPORT_FOP = range(3)
WAITING_EXPENSE_TYPE, WAITING_EXPENSE_INPUT = range(3, 5)
WAITING_PERIOD, WAITING_LOCATION, WAITING_CHANGE, WAITING_CATEGORY, WAITING_SUBCATEGORY = range(5, 10)
WAITING_SUBSUBCATEGORY = 10
WAITING_EXPENSE_DATE = 901
WAITING_MANUAL_DATE = 902
WAITING_PARTICIPANT_COMMENT = 1107
WAITING_REPORT_TYPE = 999
# Стани
WAITING_PERSON_NAME = 9999
WAITING_ACCOUNT_SELECTION = 9998
WAITING_ACCOUNT_INPUT = 9997
# Стани для dividends
WAITING_DIVIDENDS_OWNER = 8000
WAITING_DIVIDENDS_CATEGORY = 8001
WAITING_DIVIDENDS_ACCOUNT = 8002
WAITING_DIVIDENDS_AMOUNT = 8003