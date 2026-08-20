"""
models.py
Pydantic schemas used for request validation and response shaping.
"""

from pydantic import BaseModel
from typing import Optional


class ExpenseIn(BaseModel):
    amount: float
    description: str
    date: str  # format: YYYY-MM-DD
    category: Optional[str] = None  # if not given, Expense Analyzer Agent assigns it


class ExpenseOut(BaseModel):
    id: int
    amount: float
    category: str
    description: str
    date: str


class BudgetIn(BaseModel):
    category: str
    monthly_limit: float


class GoalIn(BaseModel):
    title: str
    target_amount: float
    deadline: Optional[str] = None


class GoalUpdateIn(BaseModel):
    add_amount: float


class ChatIn(BaseModel):
    message: str
