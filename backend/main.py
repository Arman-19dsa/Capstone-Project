"""
main.py
FastAPI entry point. Run with:
    uvicorn main:app --reload --port 8000

Then open frontend/index.html in a browser (or serve it separately) -
it calls these endpoints at http://localhost:8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, get_connection
from models import ExpenseIn, BudgetIn, GoalIn, GoalUpdateIn, ChatIn
from agents.orchestrator import handle_new_expense, get_dashboard_summary, handle_chat
from agents.goal_tracker import add_savings, all_goal_progress

app = FastAPI(title="Agentic Financial Learning & Expense Coach")

# Allow the frontend (served from a different port/file) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# ---------------- Expenses ----------------

@app.post("/api/expenses")
def add_expense(expense: ExpenseIn):
    result = handle_new_expense(
        amount=expense.amount,
        description=expense.description,
        date=expense.date,
        category=expense.category,
    )
    return result


@app.get("/api/expenses")
def list_expenses():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM expenses ORDER BY date DESC, id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


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
