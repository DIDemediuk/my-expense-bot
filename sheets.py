import re
import datetime
import unicodedata
import logging
from config import get_sheet_by_type, DIV_HEADERS, OTHER_HEADERS, ACCOUNT_MAP

def parse_amount(value):
    if value is None or str(value).strip() == '':
        return 0.0
    text = str(value).strip()
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[^\d,.\-]", "", text)
    text = text.replace(" ", "").replace("\u00A0", "").replace(" ", "")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    else:
        text = text.replace(",", ".")
    parts = text.split(".")
    if len(parts) > 2:
        text = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(text)
    except ValueError:
        print(f"⚠️ parse_amount fail: {repr(value)} → {repr(text)}")
        return 0.0

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

def parse_expense_simple(text: str):
    """
    Універсальний парсер для витрат типу 'other'.
    Приймає формати:
    - Просто число: "2000"
    - Число + опис: "2000 реклама"
    - Класичний формат: "ФОП2 2000 опис" або "ГОТІВКА 2000 опис"
    """
    text = text.strip()
    
    # Спроба 1: Класичний формат (ФОП/ГОТІВКА + СУМА + ОПИС)
    pattern_classic = r"^(ФОП|ГОТІВКА)\s+(.+?)\s+(\d+(?:[ ,]\d{3})*(?:[.,]\d+)?)\s*(.*)$"
    match = re.match(pattern_classic, text, re.IGNORECASE | re.UNICODE)
    if match:
        prefix, source_str, amount_str, note = match.groups()
        try:
            amount = float(amount_str.replace(',', '.').replace(' ', ''))
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
            "коментар": note.strip() if note and note.strip() else None
        }
    
    # Спроба 2: Простий формат (СУМА або СУМА + ОПИС)
    parts = text.split(maxsplit=1)
    try:
        amount = float(parts[0].replace(',', '.').replace(' ', ''))
    except (ValueError, IndexError):
        return None
    
    if amount <= 0:
        return None
    
    # Опис (якщо є)
    note = parts[1] if len(parts) > 1 else None
    
    # За замовчуванням рахунок — з контексту або "Готівка"
    return {
        "рахунок": "Готівка",  # Буде замінено з context.user_data['account'] пізніше
        "сума": amount,
        "коментар": note
    }

def add_expense_to_sheet(parsed: dict, context_data: dict, expense_type: str):
    sheet = get_sheet_by_type(expense_type)
    try:
        now = datetime.datetime.now()
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
            category_vitrat = ''
            row = [
                date_str,
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