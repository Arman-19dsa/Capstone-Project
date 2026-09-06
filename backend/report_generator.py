"""
Report Generator
Responsibility: aggregate a period's expenses, budget adherence, and
goal progress into a short natural-language summary, closing the
feedback loop described in the synopsis's Working Principle
(Capture -> Categorize -> Analyze -> Recommend -> Track).

Not a separate "agent" with its own reasoning loop -- it reuses data
already computed by the Budget Planner and Goal Tracker agents and
asks the LLM to narrate it, so it stays cheap and simple.
"""

from datetime import datetime
from database import get_connection
from agents.budget_planner import check_budget_status
from agents.goal_tracker import all_goal_progress
from llm_client import ask_llm


def get_period_expenses(year_month: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT category, SUM(amount) as total, COUNT(*) as count "
        "FROM expenses WHERE date LIKE ? GROUP BY category ORDER BY total DESC",
        (f"{year_month}%",),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def generate_report(year_month: str = None) -> dict:
    """
    Builds a structured + narrative report for the given month
    (defaults to the current month if not specified).
    year_month format: 'YYYY-MM'
    """
    if not year_month:
        year_month = datetime.now().strftime("%Y-%m")

    category_breakdown = get_period_expenses(year_month)
    total_spent = sum(c["total"] for c in category_breakdown)
    top_category = category_breakdown[0] if category_breakdown else None

    budget_status = check_budget_status(year_month)
    over_budget = [b for b in budget_status if b["status"] == "over"]
    warning_budget = [b for b in budget_status if b["status"] == "warning"]

    goals = all_goal_progress()

    if total_spent == 0:
        narrative = f"No expenses were logged for {year_month} yet. Add some expenses to generate a meaningful report."
    else:
        summary_facts = [
            f"Total spent in {year_month}: Rs.{total_spent:.0f}",
            f"Top spending category: {top_category['category']} (Rs.{top_category['total']:.0f})" if top_category else "",
            f"Categories over budget: {', '.join(b['category'] for b in over_budget) if over_budget else 'none'}",
            f"Categories nearing budget limit: {', '.join(b['category'] for b in warning_budget) if warning_budget else 'none'}",
            f"Active savings goals: {len(goals)}",
        ]
        goal_lines = [
            f"- {g['title']}: {g['percent_complete']}% complete, {g['pacing_message']}"
            for g in goals
        ]

        system_prompt = (
            "You are the reporting component of a personal finance coaching app. "
            "Write a short (4-6 sentence), encouraging but honest monthly financial "
            "summary for the user based ONLY on the facts given. Do not invent numbers. "
            "Mention what went well, what needs attention, and one concrete suggestion "
            "for next month. Write in plain prose only — do NOT use markdown formatting, "
            "asterisks, bullet points, or headers."
        )
        user_prompt = "\n".join(summary_facts) + "\n\nGoal progress:\n" + ("\n".join(goal_lines) if goal_lines else "No active goals.")

        narrative = ask_llm(system_prompt, user_prompt, max_tokens=800)

    return {
        "period": year_month,
        "total_spent": total_spent,
        "category_breakdown": category_breakdown,
        "over_budget": over_budget,
        "warning_budget": warning_budget,
        "goals": goals,
        "narrative": narrative,
    }