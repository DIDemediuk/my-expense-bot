import os
from dotenv import load_dotenv
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

# Google Sheets налаштування
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

if os.getenv("GOOGLE_CREDS"):
    # Використовуємо ключ із змінної середовища (Render)
    creds_dict = json.loads(os.getenv("GOOGLE_CREDS"))
    CREDS = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
else:
    # Локально беремо credentials.json
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
        'зарплата': ['Відділ продажів', 'Адмін', 'Директор', 'Тех. працівники'],
        'логістика': ['Транспорт', 'Склад'],
        'повернення коштів': ['Аванс 1', 'Аванс 2'],
        'змінa 1': ['Деталь 1', 'Деталь 2'],
        'маркетинг': ['Реклама', 'SMM', 'Промо', 'Креативи'],
    },
    'subsubcategories_by_subcategory': {
        'відділ продажів': ['Яна', 'Віра', 'Соня'],
        'директор': ['Олег', 'Леся'],
    },
    'changes_by_subcategory': {
        'реклама': "Рекламна кампанія",
        'дизайн': "Дизайн мерчу",
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
    "Дод. витрати": "dod_vytraty",
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
}
SUB_ASCII_TO_UKR = {v: k for k, v in SUB_UKR_TO_ASCII.items()}

SUBSUB_UKR_TO_ASCII = {
    "Яна": "yana", "Віра": "vira", "Соня": "sonya", "Олег": "oleg", "Леся": "lesya",
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

# Стани
WAITING_REPORT_PERIOD, WAITING_REPORT_OWNER, WAITING_REPORT_FOP = range(3)
WAITING_EXPENSE_TYPE, WAITING_EXPENSE_INPUT = range(3, 5)
WAITING_PERIOD, WAITING_LOCATION, WAITING_CHANGE, WAITING_CATEGORY, WAITING_SUBCATEGORY = range(5, 10)
WAITING_SUBSUBCATEGORY = 10
WAITING_EXPENSE_DATE = 901
WAITING_MANUAL_DATE = 902
WAITING_PARTICIPANT_COMMENT = 1107