from pydantic import BaseModel
from typing import Optional


class AuthIn(BaseModel):
    username: str
    password: str


class ExpenseIn(BaseModel):
    amount: float
    description: str
    date: str
    category: Optional[str] = None


class ExpenseUpdateIn(BaseModel):
    amount: Optional[float] = None
    description: Optional[str] = None
    date: Optional[str] = None
    category: Optional[str] = None


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
