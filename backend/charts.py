"""
charts.py
Aggregates expense data for the Dashboard's visualizations:
- category breakdown (doughnut)
- daily spending trend (line)
- day-of-week spending pattern (bar) -- a genuine behavioural insight,
  not just a restated total: it answers "which days do I overspend on?"
- month-over-month comparison -- current vs previous month total
- key stat callouts: average daily spend, biggest single transaction,
  and the single highest-spending day
"""

from datetime import datetime, date
import calendar
from database import get_connection


def _current_year_month():
    return datetime.now().strftime("%Y-%m")


def _previous_year_month(year_month: str) -> str:
    year, month = map(int, year_month.split("-"))
    if month == 1:
        return f"{year - 1}-12"
    return f"{year}-{month - 1:02d}"


def get_category_breakdown(year_month: str = None):
    if not year_month:
        year_month = _current_year_month()
    conn = get_connection()
    rows = conn.execute(
        "SELECT category, SUM(amount) as total FROM expenses "
        "WHERE date LIKE ? GROUP BY category ORDER BY total DESC",
        (f"{year_month}%",),
    ).fetchall()
    conn.close()
    return [{"category": r["category"], "total": r["total"]} for r in rows]


def get_daily_trend(year_month: str = None):
    if not year_month:
        year_month = _current_year_month()
    conn = get_connection()
    rows = conn.execute(
        "SELECT date, SUM(amount) as total FROM expenses "
        "WHERE date LIKE ? GROUP BY date ORDER BY date ASC",
        (f"{year_month}%",),
    ).fetchall()
    conn.close()
    return [{"date": r["date"], "total": r["total"]} for r in rows]


def get_day_of_week_pattern(year_month: str = None):
    """
    Returns total spend grouped by day of the week (Monday..Sunday) for
    the given month, so the user can see behavioural patterns like
    'I consistently overspend on weekends' rather than just a daily total.
    """
    if not year_month:
        year_month = _current_year_month()
    conn = get_connection()
    rows = conn.execute(
        "SELECT date, amount FROM expenses WHERE date LIKE ?",
        (f"{year_month}%",),
    ).fetchall()
    conn.close()

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    totals = {day: 0.0 for day in day_names}

    for row in rows:
        try:
            d = datetime.strptime(row["date"], "%Y-%m-%d").date()
            day_name = day_names[d.weekday()]
            totals[day_name] += row["amount"]
        except ValueError:
            continue

    return [{"day": day, "total": round(totals[day], 2)} for day in day_names]


def get_month_over_month(year_month: str = None):
    """
    Compares total spend in the given month against the previous
    calendar month, returning both totals and the percent change.
    """
    if not year_month:
        year_month = _current_year_month()
    previous_month = _previous_year_month(year_month)

    conn = get_connection()
    current_total = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date LIKE ?",
        (f"{year_month}%",),
    ).fetchone()["total"]
    previous_total = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE date LIKE ?",
        (f"{previous_month}%",),
    ).fetchone()["total"]
    conn.close()

    if previous_total > 0:
        percent_change = round(((current_total - previous_total) / previous_total) * 100, 1)
    elif current_total > 0:
        percent_change = None  # no previous baseline to compare against
    else:
        percent_change = 0.0

    return {
        "current_period": year_month,
        "current_total": current_total,
        "previous_period": previous_month,
        "previous_total": previous_total,
        "percent_change": percent_change,
    }


def get_key_stats(year_month: str = None):
    """
    Returns a small set of headline stats for the month: average daily
    spend, the single biggest transaction, and the single highest
    total-spend day.
    """
    if not year_month:
        year_month = _current_year_month()

    conn = get_connection()
    rows = conn.execute(
        "SELECT date, description, amount FROM expenses WHERE date LIKE ?",
        (f"{year_month}%",),
    ).fetchall()
    conn.close()

    if not rows:
        return {
            "average_daily_spend": 0,
            "biggest_expense": None,
            "highest_spend_day": None,
            "days_with_spending": 0,
        }

    total = sum(r["amount"] for r in rows)
    unique_days = set(r["date"] for r in rows)
    average_daily_spend = round(total / len(unique_days), 2) if unique_days else 0

    biggest = max(rows, key=lambda r: r["amount"])
    biggest_expense = {"description": biggest["description"], "amount": biggest["amount"], "date": biggest["date"]}

    day_totals = {}
    for r in rows:
        day_totals[r["date"]] = day_totals.get(r["date"], 0) + r["amount"]
    highest_day = max(day_totals.items(), key=lambda kv: kv[1])
    highest_spend_day = {"date": highest_day[0], "total": round(highest_day[1], 2)}

    return {
        "average_daily_spend": average_daily_spend,
        "biggest_expense": biggest_expense,
        "highest_spend_day": highest_spend_day,
        "days_with_spending": len(unique_days),
    }