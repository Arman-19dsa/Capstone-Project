"""
Orchestrator / Planner Agent
Responsibility: the entry point that coordinates the other four agents.

In this starter version the "planning" is straightforward function
calls triggered by API routes (add expense -> categorize -> check
budget -> update goal). As your team progresses, this is the file to
extend with more autonomous decision-making, e.g. the orchestrator
itself deciding which agents to call based on LLM-parsed user intent
rather than a fixed pipeline.
"""

from agents.expense_analyzer import categorize_expense
from agents.budget_planner import check_budget_status, generate_recommendation
from agents.goal_tracker import all_goal_progress
from agents.literacy_tutor import answer_question
from database import get_connection


def handle_new_expense(amount: float, description: str, date: str, category: str = None):
    """
    Full pipeline for a new expense:
    1. Expense Analyzer categorizes it (if category not already given)
    2. Saved to DB
    3. Budget Planner re-checks status for that category
    4. Returns the saved expense + any budget recommendation
    """
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


def get_dashboard_summary():
    """Aggregates data from Budget Planner + Goal Tracker for the dashboard view."""
    return {
        "budget_status": check_budget_status(),
        "goals": all_goal_progress(),
    }


def handle_chat(message: str) -> str:
    """Routes a free-text user question to the Literacy Tutor Agent."""
    return answer_question(message)
