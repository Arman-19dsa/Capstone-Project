"""
Expense Analyzer Agent
Responsibility: assign a spending category to a new transaction.

Strategy: cheap, fast rule-based keyword matching first (covers the
majority of everyday transactions and costs nothing). Only falls back
to the LLM for descriptions the rules can't confidently classify.
This mirrors what the synopsis describes: "LLM combined with a
rule-based categorization layer."
"""

import re
from llm_client import ask_llm

CATEGORY_KEYWORDS = {
    "Food": [
        "zomato", "swiggy", "restaurant", "food", "cafe", "dominos", "mess", "canteen",
        "dhaba", "hotel", "breakfast", "lunch", "dinner", "snacks", "chai", "tea",
        "coffee", "starbucks", "ccd", "pizza", "burger", "bakery", "sweets", "juice",
    ],
    "Travel": [
        "uber", "ola", "rapido", "petrol", "fuel", "diesel", "bus", "train", "irctc",
        "flight", "cab", "auto", "rickshaw", "metro", "toll", "parking", "railway",
        "airport", "indigo", "spicejet", "redbus", "train ticket", "bus ticket",
        "flight ticket",
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "mall", "shopping", "ajio", "meesho",
        "clothes", "shoes", "electronics", "decathlon", "reliance trends", "d-mart",
        "dmart", "big bazaar", "grocery", "supermarket",
    ],
    "Subscriptions": [
        "netflix", "spotify", "prime", "hotstar", "subscription", "recharge",
        "jio", "airtel", "vi ", "youtube premium", "playstation", "xbox", "app store",
        "google play", "icloud", "apple music",
    ],
    "Bills & Utilities": [
        "electricity", "bill", "wifi", "broadband", "rent", "mobile bill",
        "water bill", "gas cylinder", "maintenance", "society", "dth", "internet",
        "postpaid",
    ],
    "Education": [
        "course", "udemy", "book", "fees", "tuition", "coaching", "college",
        "exam fee", "stationery", "printout", "xerox", "library", "coursera",
        "certification",
    ],
    "Health": [
        "medicine", "pharmacy", "hospital", "doctor", "gym", "clinic", "dentist",
        "medplus", "apollo", "1mg", "pathology", "lab test", "health checkup",
    ],
    "Entertainment": [
        "movie", "bookmyshow", "book my show", "pvr", "inox", "game", "outing", "concert",
        "amusement park", "picnic", "trip", "party",
    ],
    "Personal Care": [
        "salon", "haircut", "spa", "parlour", "cosmetics", "skincare",
    ],
}

CATEGORY_LIST = list(CATEGORY_KEYWORDS.keys()) + ["Other"]


def categorize_by_rules(description: str):
    """
    Matches whole words/phrases only (not substrings), so a keyword like
    "book" won't wrongly match inside "BookMyShow". Multi-word keywords
    (e.g. "train ticket") are matched as literal phrases.
    """
    text = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, text):
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