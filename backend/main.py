"""
main.py
FastAPI entry point. Run with:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, get_connection
from models import ExpenseIn, BudgetIn, GoalIn, GoalUpdateIn, ChatIn
from agents.orchestrator import handle_new_expense, get_dashboard_summary, handle_chat, handle_csv_import
from agents.goal_tracker import add_savings, all_goal_progress
from csv_import import parse_csv_bytes
from report_generator import generate_report
from charts import get_category_breakdown, get_daily_trend


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


@app.get("/api/dashboard")
def dashboard():
    return get_dashboard_summary()
@app.get("/api/report")
def report(period: str = None):
    """Optional query param: ?period=YYYY-MM (defaults to current month)."""
    return generate_report(period)


# ---------------- Charts ----------------

@app.get("/api/charts/category-breakdown")
def category_breakdown(period: str = None):
    return get_category_breakdown(period)


@app.get("/api/charts/trend")
def spending_trend(period: str = None):
    return get_daily_trend(period)

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