"""
main.py
FastAPI entry point. Run with:
    python -m uvicorn main:app --reload --port 8000

Every data endpoint requires a logged-in user (Authorization: Bearer <token>)
and only ever reads or writes that user's own rows.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Header
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, get_connection
from models import AuthIn, ExpenseIn, ExpenseUpdateIn, BudgetIn, GoalIn, GoalUpdateIn, ChatIn
from auth import (
    register_user, login_user, create_session, get_current_user,
    extract_token, delete_session, get_username,
)
from agents.orchestrator import handle_new_expense, get_dashboard_summary, handle_chat, handle_csv_import
from agents.goal_tracker import add_savings, all_goal_progress
from csv_import import parse_csv_bytes
from pdf_import import parse_pdf_bytes, PdfImportError
from report_generator import generate_report
from charts import (
    get_category_breakdown,
    get_daily_trend,
    get_day_of_week_pattern,
    get_month_over_month,
    get_key_stats,
)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

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


# ---------------- Auth ----------------

@app.post("/api/auth/register")
def register(body: AuthIn):
    user_id, username = register_user(body.username, body.password)
    return {"token": create_session(user_id), "username": username}


@app.post("/api/auth/login")
def login(body: AuthIn):
    user_id, username = login_user(body.username, body.password)
    return {"token": create_session(user_id), "username": username}


@app.post("/api/auth/logout")
def logout(authorization: str = Header(None)):
    delete_session(extract_token(authorization))
    return {"message": "Logged out"}


@app.get("/api/auth/me")
def me(user_id: int = Depends(get_current_user)):
    return {"username": get_username(user_id)}


# ---------------- Expenses ----------------

@app.post("/api/expenses")
def add_expense(expense: ExpenseIn, user_id: int = Depends(get_current_user)):
    return handle_new_expense(
        user_id=user_id,
        amount=expense.amount,
        description=expense.description,
        date=expense.date,
        category=expense.category,
    )


@app.get("/api/expenses")
def list_expenses(user_id: int = Depends(get_current_user)):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, amount, category, description, date FROM expenses "
        "WHERE user_id = ? ORDER BY date DESC, id DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.put("/api/expenses/{expense_id}")
def update_expense(expense_id: int, update: ExpenseUpdateIn, user_id: int = Depends(get_current_user)):
    conn = get_connection()
    existing = conn.execute(
        "SELECT * FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id)
    ).fetchone()
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
        "UPDATE expenses SET amount = ?, category = ?, description = ?, date = ? "
        "WHERE id = ? AND user_id = ?",
        (new_amount, new_category, new_description, new_date, expense_id, user_id),
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
def delete_expense(expense_id: int, user_id: int = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id)
    )
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"message": "Expense deleted", "id": expense_id}


@app.post("/api/expenses/import")
async def import_expenses(file: UploadFile = File(...), user_id: int = Depends(get_current_user)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    file_bytes = await file.read()
    try:
        rows = parse_csv_bytes(file_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not parse this CSV file")

    if not rows:
        raise HTTPException(status_code=400, detail="No readable rows found in this CSV")

    return handle_csv_import(user_id, rows)


@app.post("/api/expenses/import-pdf")
async def import_expenses_pdf(
    file: UploadFile = File(...),
    password: str = Form(None),
    user_id: int = Depends(get_current_user),
):
    """
    Import a UPI-app PDF statement (e.g. PhonePe). Only DEBIT lines become
    expenses. Errors use 400 (never 401) so a wrong PDF password is not
    confused with an expired login.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a .pdf file")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="That file is too large (maximum 10 MB)")

    try:
        parsed = parse_pdf_bytes(file_bytes, password or None)
    except PdfImportError as err:
        raise HTTPException(status_code=400, detail=err.message)

    if not parsed["rows"]:
        detail = ("No payments were found in this PDF. Only money-sent (DEBIT) lines that have "
                  "a date and an amount can be imported, and this statement's layout may not be supported.")
        if parsed["unclear_lines"]:
            detail += (f" {parsed['unclear_lines']} line(s) had a date and amount but no "
                       "Debit/Credit label, so they were left out.")
        raise HTTPException(status_code=400, detail=detail)

    result = handle_csv_import(user_id, parsed["rows"])
    result["credits_skipped"] = parsed["credits_skipped"]
    result["unclear_lines"] = parsed["unclear_lines"]
    return result


# ---------------- Budgets ----------------

@app.post("/api/budgets")
def set_budget(budget: BudgetIn, user_id: int = Depends(get_current_user)):
    conn = get_connection()
    conn.execute(
        "INSERT INTO budgets (user_id, category, monthly_limit) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, category) DO UPDATE SET monthly_limit = excluded.monthly_limit",
        (user_id, budget.category, budget.monthly_limit),
    )
    conn.commit()
    conn.close()
    return {"message": "Budget saved", "category": budget.category, "monthly_limit": budget.monthly_limit}


@app.get("/api/budgets")
def get_budgets_endpoint(user_id: int = Depends(get_current_user)):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, category, monthly_limit FROM budgets WHERE user_id = ?", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ---------------- Goals ----------------

@app.post("/api/goals")
def create_goal(goal: GoalIn, user_id: int = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO goals (user_id, title, target_amount, deadline) VALUES (?, ?, ?, ?)",
        (user_id, goal.title, goal.target_amount, goal.deadline),
    )
    conn.commit()
    goal_id = cur.lastrowid
    conn.close()
    return {"id": goal_id, "message": "Goal created"}


@app.get("/api/goals")
def list_goals(user_id: int = Depends(get_current_user)):
    return all_goal_progress(user_id)


@app.post("/api/goals/{goal_id}/add")
def update_goal(goal_id: int, update: GoalUpdateIn, user_id: int = Depends(get_current_user)):
    if not add_savings(user_id, goal_id, update.add_amount):
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"message": "Savings updated"}


# ---------------- Dashboard ----------------

@app.get("/api/dashboard")
def dashboard(user_id: int = Depends(get_current_user)):
    return get_dashboard_summary(user_id)


# ---------------- Reports ----------------

@app.get("/api/report")
def report(period: str = None, user_id: int = Depends(get_current_user)):
    """Optional query param: ?period=YYYY-MM (defaults to current month)."""
    return generate_report(user_id, period)


# ---------------- Charts & Insights ----------------

@app.get("/api/charts/category-breakdown")
def category_breakdown(period: str = None, user_id: int = Depends(get_current_user)):
    return get_category_breakdown(user_id, period)


@app.get("/api/charts/trend")
def spending_trend(period: str = None, user_id: int = Depends(get_current_user)):
    return get_daily_trend(user_id, period)


@app.get("/api/charts/day-of-week")
def day_of_week(period: str = None, user_id: int = Depends(get_current_user)):
    return get_day_of_week_pattern(user_id, period)


@app.get("/api/charts/month-over-month")
def month_over_month(period: str = None, user_id: int = Depends(get_current_user)):
    return get_month_over_month(user_id, period)


@app.get("/api/charts/key-stats")
def key_stats(period: str = None, user_id: int = Depends(get_current_user)):
    return get_key_stats(user_id, period)


# ---------------- Chat / Literacy Tutor ----------------

@app.post("/api/chat")
def chat(chat_in: ChatIn, user_id: int = Depends(get_current_user)):
    reply = handle_chat(chat_in.message)

    conn = get_connection()
    conn.execute(
        "INSERT INTO chat_history (user_id, role, message) VALUES (?, 'user', ?)",
        (user_id, chat_in.message),
    )
    conn.execute(
        "INSERT INTO chat_history (user_id, role, message) VALUES (?, 'assistant', ?)",
        (user_id, reply),
    )
    conn.commit()
    conn.close()

    return {"reply": reply}


@app.get("/api/chat/history")
def chat_history(user_id: int = Depends(get_current_user)):
    conn = get_connection()
    rows = conn.execute(
        "SELECT role, message, created_at FROM chat_history WHERE user_id = ? ORDER BY id ASC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/")
def root():
    return {"status": "running", "message": "Agentic Financial Coach API. See /docs for endpoints."}
