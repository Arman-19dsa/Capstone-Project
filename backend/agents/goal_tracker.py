from datetime import datetime, date
from database import get_connection


def get_goals(user_id: int):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM goals WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_savings(user_id: int, goal_id: int, amount: float) -> bool:
    """Returns False if the goal does not exist or belongs to another user."""
    conn = get_connection()
    cur = conn.execute(
        "UPDATE goals SET saved_amount = saved_amount + ? WHERE id = ? AND user_id = ?",
        (amount, goal_id, user_id),
    )
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated


def goal_progress(goal: dict) -> dict:
    target = goal["target_amount"]
    saved = goal["saved_amount"]
    pct = round((saved / target) * 100, 1) if target > 0 else 0

    pacing_message = "No deadline set."
    if goal.get("deadline"):
        try:
            deadline_date = datetime.strptime(goal["deadline"], "%Y-%m-%d").date()
            days_left = (deadline_date - date.today()).days
            remaining = max(target - saved, 0)
            if days_left <= 0:
                pacing_message = "Deadline has passed." if remaining > 0 else "Goal completed on time."
            elif remaining == 0:
                pacing_message = "Goal already achieved."
            else:
                needed_per_day = remaining / days_left
                pacing_message = f"Save about Rs.{needed_per_day:.0f}/day for {days_left} days to reach this goal on time."
        except ValueError:
            pacing_message = "Invalid deadline format."

    return {
        "id": goal["id"],
        "title": goal["title"],
        "target_amount": target,
        "saved_amount": saved,
        "percent_complete": pct,
        "deadline": goal.get("deadline"),
        "pacing_message": pacing_message,
    }


def all_goal_progress(user_id: int):
    return [goal_progress(g) for g in get_goals(user_id)]
