"""
charts.py
Aggregates expense data into the shapes Chart.js needs for the
Dashboard's two visualizations: a category breakdown (doughnut) and
a daily spending trend (line), both for a given month.
"""

from datetime import datetime
from database import get_connection


def get_category_breakdown(year_month: str = None):
    """Returns [{category, total}, ...] for all categories in the given month."""
    if not year_month:
        year_month = datetime.now().strftime("%Y-%m")

    conn = get_connection()
    rows = conn.execute(
        "SELECT category, SUM(amount) as total FROM expenses "
        "WHERE date LIKE ? GROUP BY category ORDER BY total DESC",
        (f"{year_month}%",),
    ).fetchall()
    conn.close()
    return [{"category": r["category"], "total": r["total"]} for r in rows]


def get_daily_trend(year_month: str = None):
    """
    Returns [{date, total}, ...] one entry per calendar day that had at
    least one expense in the given month, sorted by date ascending.
    """
    if not year_month:
        year_month = datetime.now().strftime("%Y-%m")

    conn = get_connection()
    rows = conn.execute(
        "SELECT date, SUM(amount) as total FROM expenses "
        "WHERE date LIKE ? GROUP BY date ORDER BY date ASC",
        (f"{year_month}%",),
    ).fetchall()
    conn.close()
    return [{"date": r["date"], "total": r["total"]} for r in rows]