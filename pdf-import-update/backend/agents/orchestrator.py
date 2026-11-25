from collections import Counter

from agents.expense_analyzer import categorize_expense
from agents.budget_planner import check_budget_status, generate_recommendation
from agents.goal_tracker import all_goal_progress
from agents.literacy_tutor import answer_question
from database import get_connection


def handle_new_expense(user_id: int, amount: float, description: str, date: str, category: str = None):
    if not category:
        category = categorize_expense(description)

    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO expenses (user_id, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, description, date),
    )
    conn.commit()
    expense_id = cur.lastrowid
    conn.close()

    budget_status = check_budget_status(user_id)
    matching = next((b for b in budget_status if b["category"] == category), None)
    recommendation = generate_recommendation(matching) if matching else None

    return {
        "expense": {
            "id": expense_id,
            "amount": amount,
            "category": category,
            "description": description,
            "date": date,
        },
        "budget_recommendation": recommendation,
    }


def handle_csv_import(user_id: int, rows: list):
    """
    Shared by CSV and PDF import. Rows that already exist in this user's
    account (same date, description and amount) are skipped, so uploading
    the same statement twice, or two statements that overlap, does not
    create double expenses. Identical rows inside ONE file are all kept
    (two real purchases of the same item on the same day are legitimate).
    """
    conn = get_connection()

    existing = Counter()
    for r in conn.execute(
        "SELECT date, description, amount FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchall():
        existing[(r["date"], (r["description"] or "").strip(), round(r["amount"], 2))] += 1

    imported = 0
    skipped = 0
    duplicates = 0
    affected_categories = set()

    for row in rows:
        try:
            amount = float(row["amount"])
            description = row["description"].strip()
            date = row["date"].strip()
        except (KeyError, ValueError, AttributeError):
            skipped += 1
            continue

        if not description or amount <= 0:
            skipped += 1
            continue

        key = (date, description, round(amount, 2))
        if existing[key] > 0:
            existing[key] -= 1
            duplicates += 1
            continue

        category = row.get("category") or categorize_expense(description)
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, description, date),
        )
        affected_categories.add(category)
        imported += 1

    conn.commit()
    conn.close()

    budget_status = check_budget_status(user_id)
    recommendations = [
        {"category": b["category"], "tip": generate_recommendation(b)}
        for b in budget_status
        if b["category"] in affected_categories and b["status"] != "ok"
    ]

    return {
        "imported": imported,
        "skipped": skipped,
        "duplicates": duplicates,
        "budget_recommendations": recommendations,
    }


def get_dashboard_summary(user_id: int):
    return {
        "budget_status": check_budget_status(user_id),
        "goals": all_goal_progress(user_id),
    }


def handle_chat(message: str) -> str:
    return answer_question(message)
