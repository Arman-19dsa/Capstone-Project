"""
Expense Analyzer Agent
Responsibility: assign a spending category to a new transaction.

Strategy: cheap, fast rule-based keyword matching first (covers the
majority of everyday transactions and costs nothing). Only falls back
to the LLM for descriptions the rules can't confidently classify.
This mirrors what the synopsis describes: "LLM combined with a
rule-based categorization layer."
"""

from llm_client import ask_llm

CATEGORY_KEYWORDS = {
    "Food": ["zomato", "swiggy", "restaurant", "food", "cafe", "dominos", "mess", "canteen"],
    "Travel": ["uber", "ola", "rapido", "petrol", "fuel", "bus", "train", "irctc", "flight"],
    "Shopping": ["amazon", "flipkart", "myntra", "mall", "shopping"],
    "Subscriptions": ["netflix", "spotify", "prime", "hotstar", "subscription", "recharge"],
    "Bills & Utilities": ["electricity", "bill", "wifi", "broadband", "rent", "mobile bill"],
    "Education": ["course", "udemy", "book", "fees", "tuition", "coaching"],
    "Health": ["medicine", "pharmacy", "hospital", "doctor", "gym"],
    "Entertainment": ["movie", "bookmyshow", "pvr", "game", "outing"],
}

CATEGORY_LIST = list(CATEGORY_KEYWORDS.keys()) + ["Other"]


def categorize_by_rules(description: str):
    text = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return None


def categorize_with_llm(description: str) -> str:
    system_prompt = (
        "You are the Expense Analyzer Agent in a personal finance app. "
        f"Classify the transaction into exactly one of these categories: {', '.join(CATEGORY_LIST)}. "
        "Reply with ONLY the category name, nothing else."
    )
    result = ask_llm(system_prompt, f"Transaction description: {description}", max_tokens=10)
    result = result.strip()
    return result if result in CATEGORY_LIST else "Other"


def categorize_expense(description: str) -> str:
    """Public entry point used by the orchestrator / API layer."""
    rule_result = categorize_by_rules(description)
    if rule_result:
        return rule_result
    return categorize_with_llm(description)
