"""
Orchestrator / Planner Agent
"""

from agents.expense_analyzer import categorize_expense
from agents.budget_planner import check_budget_status, generate_recommendation
from agents.goal_tracker import all_goal_progress
from agents.literacy_tutor import answer_question
from database import get_connection


def handle_new_expense(amount: float, description: str, date: str, category: str = None):
    if not category:
        category = categorize_expense(description)

    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO expenses (amount, category, description, date) VALUES (?, ?, ?, ?)",
        (amount, category, description, date),
    )
    conn.commit()
    expense_id = cur.lastrowid
    conn.close()

    budget_status = check_budget_status()
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


def handle_csv_import(rows: list):
    conn = get_connection()
    imported = 0
    skipped = 0
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

        category = row.get("category") or categorize_expense(description)
        conn.execute(
            "INSERT INTO expenses (amount, category, description, date) VALUES (?, ?, ?, ?)",
            (amount, category, description, date),
        )
        affected_categories.add(category)
        imported += 1

    conn.commit()
    conn.close()

    budget_status = check_budget_status()
    recommendations = [
        {"category": b["category"], "tip": generate_recommendation(b)}
        for b in budget_status
        if b["category"] in affected_categories and b["status"] != "ok"
    ]

    return {
        "imported": imported,
        "skipped": skipped,
        "budget_recommendations": recommendations,
    }


def get_dashboard_summary():
    return {
        "budget_status": check_budget_status(),
        "goals": all_goal_progress(),
    }


def handle_chat(message: str) -> str:
    return answer_question(message)