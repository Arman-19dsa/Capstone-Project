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
    {
        "topic": "EMI (Equated Monthly Installment)",
        "text": (
            "An EMI is a fixed monthly payment made to repay a loan (home, car, personal, or "
            "education loan) over a set period. Each EMI covers both principal and interest, "
            "with the interest portion typically higher in early installments. A lower EMI over "
            "a longer tenure means paying more total interest over the life of the loan."
        ),
    },
    {
        "topic": "Inflation",
        "text": (
            "Inflation is the rate at which the general price level of goods and services rises "
            "over time, reducing the purchasing power of money. If inflation is 6% annually, "
            "something costing Rs.100 today will cost roughly Rs.106 next year. Savings kept in "
            "low-interest accounts can lose real value if the interest rate earned is below inflation."
        ),
    },
    {
        "topic": "Mutual Funds",
        "text": (
            "A mutual fund pools money from many investors to invest in a diversified portfolio "
            "of stocks, bonds, or other securities, managed by a professional fund manager. "
            "Investors buy units of the fund and returns depend on the performance of the "
            "underlying assets. Mutual funds carry market risk and are not guaranteed returns."
        ),
    },
    {
        "topic": "PPF (Public Provident Fund)",
        "text": (
            "The Public Provident Fund is a government-backed long-term savings scheme in India "
            "with a 15-year lock-in period, offering tax-free interest and tax deduction on "
            "contributions under Section 80C. It is considered low-risk since it is backed by "
            "the government, making it suitable for long-term, conservative savings goals."
        ),
    },
    {
        "topic": "NPS (National Pension System)",
        "text": (
            "The National Pension System is a government-regulated retirement savings scheme "
            "where contributions are invested in a mix of equity, corporate bonds, and government "
            "securities based on the subscriber's chosen allocation. On retirement, part of the "
            "corpus can be withdrawn and the remainder must be used to purchase an annuity."
        ),
    },
    {
        "topic": "Term Insurance",
        "text": (
            "Term insurance is a pure life insurance policy that pays a fixed sum to nominees if "
            "the policyholder dies within the policy term, with no maturity payout if they "
            "survive the term. It offers high coverage at relatively low premiums compared to "
            "investment-linked insurance plans, making it a cost-effective way to protect dependents."
        ),
    },
    {
        "topic": "Health Insurance",
        "text": (
            "Health insurance covers medical expenses such as hospitalization, surgery, and "
            "sometimes outpatient treatment, in exchange for a premium paid periodically. Having "
            "adequate health cover reduces the risk of a medical emergency depleting savings or "
            "forcing high-interest borrowing; coverage should be reviewed periodically as costs rise."
        ),
    },
    {
        "topic": "Income Tax Basics (India)",
        "text": (
            "In India, individuals pay income tax based on slab rates that increase with income "
            "level, under either the Old Tax Regime (with various deductions and exemptions like "
            "80C) or the New Tax Regime (lower rates but fewer deductions). Filing an income tax "
            "return (ITR) annually is mandatory above certain income thresholds, even if tax is nil."
        ),
    },
    {
        "topic": "Diversification",
        "text": (
            "Diversification means spreading investments across different asset classes (equity, "
            "debt, gold, real estate) or within an asset class (multiple stocks or sectors) to "
            "reduce risk. The idea is that poor performance in one investment is offset by "
            "stability or gains in others, reducing the impact of any single investment's failure."
        ),
    },
    {
        "topic": "UPI Safety and Digital Payment Fraud",
        "text": (
            "UPI transactions are generally secure, but fraud commonly occurs through phishing "
            "links, fake payment requests, or QR codes that trick users into approving a payment "
            "instead of receiving one. Users should never share their UPI PIN, OTP, or approve "
            "unknown payment collect requests, since a UPI PIN is only needed to send money, not receive it."
        ),
    },
    {
        "topic": "Fixed Deposit vs Recurring Deposit",
        "text": (
            "A Fixed Deposit (FD) involves investing a lump sum for a fixed tenure at a fixed "
            "interest rate, suited for one-time savings. A Recurring Deposit (RD) involves "
            "depositing a fixed amount every month for a fixed tenure, suited for building savings "
            "gradually. Both are low-risk, bank-guaranteed instruments with fairly predictable returns."
        ),
    },
    {
        "topic": "Digital Lending Apps and Instant Loan Risks",
        "text": (
            "Instant loan apps offer quick, minimal-documentation credit but often carry very high "
            "effective interest rates and aggressive recovery practices. Users should verify an "
            "app is registered with or partnered with an RBI-regulated NBFC or bank before "
            "borrowing, and should carefully check the total repayment amount, not just the loan amount offered."
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