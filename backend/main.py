"""
main.py
FastAPI entry point. Run with:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, get_connection
from models import ExpenseIn, ExpenseUpdateIn, BudgetIn, GoalIn, GoalUpdateIn, ChatIn
from agents.orchestrator import handle_new_expense, get_dashboard_summary, handle_chat, handle_csv_import
from agents.goal_tracker import add_savings, all_goal_progress
from csv_import import parse_csv_bytes
from report_generator import generate_report
from charts import (
    get_category_breakdown,
    get_daily_trend,
    get_day_of_week_pattern,
    get_month_over_month,
    get_key_stats,
)

app = FastAPI(title="Agentic Financial Learning & Expense Coach")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# ---------------- Expenses ----------------

@app.post("/api/expenses")
def add_expense(expense: ExpenseIn):
    return handle_new_expense(
        amount=expense.amount,
        description=expense.description,
        date=expense.date,
        category=expense.category,
    )


@app.get("/api/expenses")
def list_expenses():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM expenses ORDER BY date DESC, id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.put("/api/expenses/{expense_id}")
def update_expense(expense_id: int, update: ExpenseUpdateIn):
    conn = get_connection()
    existing = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Expense not found")

    new_amount = update.amount if update.amount is not None else existing["amount"]
    new_description = update.description if update.description is not None else existing["description"]
    new_date = update.date if update.date is not None else existing["date"]

    if update.category is not None:
        new_category = update.category
    elif update.description is not None and update.description != existing["description"]:
        from agents.expense_analyzer import categorize_expense
        new_category = categorize_expense(update.description)
    else:
        new_category = existing["category"]

    conn.execute(
        "UPDATE expenses SET amount = ?, category = ?, description = ?, date = ? WHERE id = ?",
        (new_amount, new_category, new_description, new_date, expense_id),
    )
    conn.commit()
    conn.close()

    return {
        "id": expense_id,
        "amount": new_amount,
        "category": new_category,
        "description": new_description,
        "date": new_date,
    }


@app.delete("/api/expenses/{expense_id}")
def delete_expense(expense_id: int):
    conn = get_connection()
    existing = conn.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Expense not found")

    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()
    return {"message": "Expense deleted", "id": expense_id}


@app.post("/api/expenses/import")
async def import_expenses(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    file_bytes = await file.read()
    try:
        rows = parse_csv_bytes(file_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not parse this CSV file")

    if not rows:
        raise HTTPException(status_code=400, detail="No readable rows found in this CSV")

    return handle_csv_import(rows)


# ---------------- Budgets ----------------

@app.post("/api/budgets")
def set_budget(budget: BudgetIn):
    conn = get_connection()
    conn.execute(
        "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?) "
        "ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit",
        (budget.category, budget.monthly_limit),
    )
    conn.commit()
    conn.close()
    return {"message": "Budget saved", "category": budget.category, "monthly_limit": budget.monthly_limit}


@app.get("/api/budgets")
def get_budgets_endpoint():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM budgets").fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ---------------- Goals ----------------

@app.post("/api/goals")
def create_goal(goal: GoalIn):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO goals (title, target_amount, deadline) VALUES (?, ?, ?)",
        (goal.title, goal.target_amount, goal.deadline),
    )
    conn.commit()
    goal_id = cur.lastrowid
    conn.close()
    return {"id": goal_id, "message": "Goal created"}


@app.get("/api/goals")
def list_goals():
    return all_goal_progress()


@app.post("/api/goals/{goal_id}/add")
def update_goal(goal_id: int, update: GoalUpdateIn):
    add_savings(goal_id, update.add_amount)
    return {"message": "Savings updated"}


# ---------------- Dashboard ----------------

@app.get("/api/dashboard")
def dashboard():
    return get_dashboard_summary()


# ---------------- Reports ----------------

@app.get("/api/report")
def report(period: str = None):
    """Optional query param: ?period=YYYY-MM (defaults to current month)."""
    return generate_report(period)


# ---------------- Charts & Insights ----------------

@app.get("/api/charts/category-breakdown")
def category_breakdown(period: str = None):
    return get_category_breakdown(period)


@app.get("/api/charts/trend")
def spending_trend(period: str = None):
    return get_daily_trend(period)


@app.get("/api/charts/day-of-week")
def day_of_week(period: str = None):
    return get_day_of_week_pattern(period)


@app.get("/api/charts/month-over-month")
def month_over_month(period: str = None):
    return get_month_over_month(period)


@app.get("/api/charts/key-stats")
def key_stats(period: str = None):
    return get_key_stats(period)


# ---------------- Chat / Literacy Tutor ----------------

@app.post("/api/chat")
def chat(chat_in: ChatIn):
    reply = handle_chat(chat_in.message)

    conn = get_connection()
    conn.execute("INSERT INTO chat_history (role, message) VALUES ('user', ?)", (chat_in.message,))
    conn.execute("INSERT INTO chat_history (role, message) VALUES ('assistant', ?)", (reply,))
    conn.commit()
    conn.close()

    return {"reply": reply}


@app.get("/api/chat/history")
def chat_history():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM chat_history ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/")
def root():
    return {"status": "running", "message": "Agentic Financial Coach API. See /docs for endpoints."}