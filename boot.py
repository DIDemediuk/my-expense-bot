import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Доступ до API
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE)
GS_CLIENT = gspread.authorize(CREDS)

# Відкрити таблицю за назвою
SHEET = GS_CLIENT.open("Expenses").worksheet("Expenses")

# Додати рядок
SHEET.append_row(["2025-10-17", "ФОП Радул І.", "Ваня", "Мантра", 3600, "ЗП Андрій"])
