"""
Financial Literacy Tutor Agent
Responsibility: answer financial literacy questions grounded in a
curated knowledge base (RAG), instead of letting the LLM answer freely
and risk hallucinated facts.

This starter version uses simple keyword-overlap retrieval over a
small in-memory knowledge base so the whole team can run it with zero
extra setup. Once this works end-to-end, swap `retrieve()` for a real
vector search using Chroma (see README for the upgrade path) without
touching any other file.
"""

from llm_client import ask_llm

# --- Curated knowledge base (expand this as your team researches more topics) ---
KNOWLEDGE_BASE = [
    {
        "topic": "SIP",
        "text": (
            "A Systematic Investment Plan (SIP) is a method of investing a fixed amount "
            "regularly (e.g., monthly) into a mutual fund. It uses rupee-cost averaging, "
            "meaning you buy more units when prices are low and fewer when prices are high, "
            "reducing the impact of market volatility over time."
        ),
    },
    {
        "topic": "Emergency Fund",
        "text": (
            "An emergency fund is money set aside to cover 3-6 months of essential expenses "
            "in case of job loss, medical emergency, or other unexpected events. It should be "
            "kept in a liquid, low-risk instrument such as a savings account or liquid mutual fund, "
            "not invested in volatile assets."
        ),
    },
    {
        "topic": "Credit Score",
        "text": (
            "A credit score (e.g., CIBIL score in India) is a number between 300-900 that reflects "
            "your creditworthiness based on repayment history, credit utilization, and loan history. "
            "A score above 750 is generally considered good and improves loan/credit card approval chances."
        ),
    },
    {
        "topic": "Credit Card vs Debit Card",
        "text": (
            "A debit card spends money directly from your bank account, so you cannot spend more "
            "than you have. A credit card lets you borrow up to a limit and repay later; used responsibly "
            "(paying the full bill on time) it can build credit history, but carrying a balance incurs high interest."
        ),
    },
    {
        "topic": "50-30-20 Rule",
        "text": (
            "The 50-30-20 budgeting rule suggests allocating 50% of after-tax income to needs "
            "(rent, food, bills), 30% to wants (entertainment, shopping), and 20% to savings and "
            "debt repayment. It is a simple starting framework, not a strict requirement."
        ),
    },
    {
        "topic": "Compound Interest",
        "text": (
            "Compound interest is interest calculated on both the initial principal and the "
            "accumulated interest from previous periods. Starting to save or invest early lets "
            "compounding work over a longer time horizon, significantly increasing final returns."
        ),
    },
]


def retrieve(query: str, top_k: int = 2):
    """
    Very simple keyword-overlap retrieval (placeholder for real vector search).
    Scores each KB entry by how many query words appear in its topic/text.
    """
    query_words = set(query.lower().split())
    scored = []
    for entry in KNOWLEDGE_BASE:
        entry_words = set((entry["topic"] + " " + entry["text"]).lower().split())
        overlap = len(query_words & entry_words)
        if overlap > 0:
            scored.append((overlap, entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:top_k]]


def answer_question(query: str) -> str:
    relevant_docs = retrieve(query)

    if not relevant_docs:
        context = "No directly relevant reference material was found in the knowledge base."
    else:
        context = "\n\n".join(f"[{doc['topic']}]: {doc['text']}" for doc in relevant_docs)

    system_prompt = (
        "You are the Financial Literacy Tutor Agent in a personal finance coaching app. "
        "Answer the user's question in simple, clear language using ONLY the reference "
        "material provided below. If the reference material does not cover the question, "
        "say so honestly instead of guessing.\n\n"
        f"Reference material:\n{context}"
    )
    return ask_llm(system_prompt, query, max_tokens=250)
