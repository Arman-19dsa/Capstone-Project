from datetime import datetime
from database import get_connection
from llm_client import ask_llm


def get_month_spend_by_category(user_id: int, year_month: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT category, SUM(amount) as total FROM expenses "
        "WHERE user_id = ? AND date LIKE ? GROUP BY category",
        (user_id, f"{year_month}%"),
    ).fetchall()
    conn.close()
    return {row["category"]: row["total"] for row in rows}


def get_budgets(user_id: int):
    conn = get_connection()
    rows = conn.execute(
        "SELECT category, monthly_limit FROM budgets WHERE user_id = ?", (user_id,)
    ).fetchall()
    conn.close()
    return {row["category"]: row["monthly_limit"] for row in rows}


def check_budget_status(user_id: int, year_month: str = None):
    if not year_month:
        year_month = datetime.now().strftime("%Y-%m")
    spend = get_month_spend_by_category(user_id, year_month)
    budgets = get_budgets(user_id)

    status = []
    for category, limit in budgets.items():
        spent = spend.get(category, 0)
        pct = round((spent / limit) * 100, 1) if limit > 0 else 0
        if pct >= 100:
            flag = "over"
        elif pct >= 80:
            flag = "warning"
        else:
            flag = "ok"
        status.append({
            "category": category,
            "spent": spent,
            "limit": limit,
            "percent_used": pct,
            "status": flag,
        })
    return status


def generate_recommendation(category_status: dict) -> str:
    if category_status["status"] == "ok":
        return f"You're within budget for {category_status['category']}. No action needed."

    system_prompt = (
        "You are the Budget Planner Agent in a personal finance coaching app. "
        "Give ONE short, practical, encouraging tip (max 2 sentences) to help "
        "the user avoid overspending in the given category. Be specific and actionable."
    )
    user_prompt = (
        f"Category: {category_status['category']}\n"
        f"Spent so far: Rs.{category_status['spent']}\n"
        f"Monthly limit: Rs.{category_status['limit']}\n"
        f"Percent used: {category_status['percent_used']}%\n"
        f"Status: {category_status['status']}"
    )
    return ask_llm(system_prompt, user_prompt, max_tokens=100)
