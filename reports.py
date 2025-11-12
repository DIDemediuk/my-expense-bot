import datetime
from collections import defaultdict
import logging
import re
from config import SHEET_MAP, DIV_HEADERS, OTHER_HEADERS, CONFIG_OTHER
from sheets import parse_amount

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
                if amount > 0:
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
            if location_groups:
                report_lines.append("\n📍 Розхід по локаціях:")
                for loc, amt in sorted(location_groups.items(), key=lambda x: x[1], reverse=True):
                    pct = (amt / expense_total * 100) if expense_total > 0 else 0
                    report_lines.append(f"  • {loc}: {amt:,.2f} грн ({pct:.1f}%)")
            if income_category_groups:
                total_inc_cat = sum(income_category_groups.values())
                if total_inc_cat > 0:
                    report_lines.append("\n🟢 Дохід по категоріях:")
                    for cat, amt in sorted(income_category_groups.items(), key=lambda x: x[1], reverse=True):
                        if amt > 0:
                            pct = (amt / total_inc_cat * 100)
                            report_lines.append(f"  • {cat}: {amt:,.2f} грн ({pct:.1f}%)")
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
    from config import get_sheet_by_type
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
                    row_date = datetime.datetime.strptime(row_date_str, "%d.%m.%Y %H:%M")
                else:
                    row_date = datetime.datetime.strptime(row_date_str, "%d.%m.%Y")
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
        else:
            category = row.get("Дод. категорії", "Невідомо")
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

def generate_period_report(period_name: str):
    """
    Звіт по періоду з детальною структурою:
    - Загальний дохід
    - Загальні витрати
    - Різниця (заробіток)
    - Розбивка витрат по категоріях
    """
    try:
        period_lower = period_name.strip().lower()
        income_total = 0.0
        expense_total = 0.0
        
        sheet = SHEET_MAP['other']
        rows = sheet.get_all_records(expected_headers=OTHER_HEADERS)
        logging.info(f"Звіт по періоду '{period_name}': завантажено {len(rows)} рядків")
        
        expense_category_groups = defaultdict(float)
        
        for row in rows:
            period = str(row.get("Період", "")).strip().lower()
            type_ = str(row.get("Група", "")).strip().lower()
            
            if period == period_lower:
                raw_sum = row.get("Сума", "")
                amount = parse_amount(raw_sum)
                
                if amount > 0:
                    if "дохід" in type_:
                        income_total += amount
                    elif "розхід" in type_:
                        expense_total += amount
                        # Збираємо категорії витрат
                        category = str(row.get("Категорії", "")).strip()
                        if not category:
                            category = str(row.get("Дод. категорії", "Інше")).strip()
                        if category:
                            expense_category_groups[category] += amount
        
        # Розрахунок різниці (заробітку)
        profit = income_total - expense_total
        expense_percent = (expense_total / income_total * 100) if income_total > 0 else 0
        
        # Формування звіту
        report_lines = [
            f"📊 *Фінансовий звіт: {period_name}*\n",
            f"──────────────────────\n",
            f"🟢 *Загальний дохід:* {income_total:,.2f} грн\n",
            f"🔴 *Загальні витрати:* {expense_total:,.2f} грн ({expense_percent:.1f}% від доходу)\n",
            f"💰 *Заробіток (різниця):* {profit:,.2f} грн",
        ]
        
        # Розбивка витрат по категоріях
        if expense_category_groups:
            report_lines.append("\n──────────────────────")
            report_lines.append("📋 *Витрати по категоріях:*\n")
            
            for cat, amt in sorted(expense_category_groups.items(), key=lambda x: x[1], reverse=True):
                if amt > 0:
                    pct = (amt / expense_total * 100) if expense_total > 0 else 0
                    report_lines.append(f"  • {cat}: {amt:,.2f} грн ({pct:.1f}%)")
        
        report = "\n".join(report_lines)
        logging.info(f"Звіт '{period_name}': дохід={income_total}, витрати={expense_total}, заробіток={profit}")
        return report, 'Markdown'
        
    except Exception as e:
        logging.exception("Помилка у generate_period_report")
        return f"❌ Помилка: {e}", None


def generate_daily_report(expense_type=None):
    from config import SHEET_MAP, DIV_HEADERS, OTHER_HEADERS
    today = datetime.date.today().strftime("%d.%m.%Y")
    report_lines = [f"📅 *Звіт за день: {today}*"]
    sheets_data = {}
    for etype, sheet in SHEET_MAP.items():
        if expense_type and etype != expense_type:
            continue
        try:
            headers = DIV_HEADERS if etype == 'dividends' else OTHER_HEADERS
            rows = sheet.get_all_records(expected_headers=headers)
            today_rows = []
            for row in rows:
                row_date_str = row.get("Дата", "")
                if row_date_str.startswith(today):
                    today_rows.append(row)
            sheets_data[etype] = today_rows
        except Exception as e:
            logging.error(f"Помилка для {etype}: {e}")
            continue
    if not any(sheets_data.values()):
        return report_lines[0] + "\n📭 Немає витрат за день."
    from collections import defaultdict
    totals = defaultdict(lambda: defaultdict(lambda: {'sum': 0.0, 'count': 0}))
    for etype, rows in sheets_data.items():
        col_fop = "Джерело" if etype == 'dividends' else "Рахунок"
        for row in rows:
            fop = row.get(col_fop, "Невідомо").strip()
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
    return "\n".join(report_lines), 'Markdown'


def generate_cashflow_report(period_name: str):
    """
    Звіт про кешфлоу (рух грошей) по рахунках за період:
    - По кожному рахунку: надходження, витрати, баланс
    - Загальний підсумок
    """
    try:
        period_lower = period_name.strip().lower()
        
        # Словник для зберігання даних по рахунках
        # {account: {'income': amount, 'expense': amount}}
        accounts_flow = defaultdict(lambda: {'income': 0.0, 'expense': 0.0})
        
        sheet = SHEET_MAP['other']
        rows = sheet.get_all_records(expected_headers=OTHER_HEADERS)
        logging.info(f"Cashflow звіт '{period_name}': завантажено {len(rows)} рядків")
        
        for row in rows:
            period = str(row.get("Період", "")).strip().lower()
            type_ = str(row.get("Група", "")).strip().lower()
            account = str(row.get("Рахунок", "Невідомо")).strip()
            
            if period == period_lower:
                raw_sum = row.get("Сума", "")
                amount = parse_amount(raw_sum)
                
                if amount > 0:
                    if "дохід" in type_:
                        accounts_flow[account]['income'] += amount
                    elif "розхід" in type_:
                        accounts_flow[account]['expense'] += amount
        
        # Формування звіту
        report_lines = [
            f"💰 *Звіт про кешфлоу: {period_name}*\n",
            f"──────────────────────\n"
        ]
        
        total_income = 0.0
        total_expense = 0.0
        
        # Звіт по кожному рахунку
        for account in sorted(accounts_flow.keys()):
            data = accounts_flow[account]
            income = data['income']
            expense = data['expense']
            balance = income - expense
            
            total_income += income
            total_expense += expense
            
            # Емодзі для балансу
            balance_emoji = "🟢" if balance > 0 else "🔴" if balance < 0 else "⚪"
            
            report_lines.append(f"💳 *{account}*")
            report_lines.append(f"  ↗️ Надходження: {income:,.2f} грн")
            report_lines.append(f"  ↘️ Витрати: {expense:,.2f} грн")
            report_lines.append(f"  {balance_emoji} Баланс: {balance:,.2f} грн\n")
        
        # Загальний підсумок
        total_balance = total_income - total_expense
        report_lines.append("──────────────────────")
        report_lines.append("📊 *ЗАГАЛОМ:*")
        report_lines.append(f"  ↗️ Всі надходження: {total_income:,.2f} грн")
        report_lines.append(f"  ↘️ Всі витрати: {total_expense:,.2f} грн")
        report_lines.append(f"  💰 Загальний баланс: {total_balance:,.2f} грн")
        
        report = "\n".join(report_lines)
        logging.info(f"Cashflow '{period_name}': надходження={total_income}, витрати={total_expense}")
        return report, 'Markdown'
        
    except Exception as e:
        logging.exception("Помилка у generate_cashflow_report")
        return f"❌ Помилка: {e}", None