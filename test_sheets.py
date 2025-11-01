import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE)
GS_CLIENT = gspread.authorize(CREDS)

# 👇 Заміни на твої точні назви
SHEET = GS_CLIENT.open("Expenses").worksheet("Expenses")

timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
test_row = [timestamp, "Тест акаунт", "Тест користувач", "Тест категорія", 123.45, "Тестовий запис"]

SHEET.append_row(test_row)

print("✅ Рядок додано:", test_row)
