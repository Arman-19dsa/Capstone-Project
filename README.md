# Agentic Financial Learning & Expense Coach

A web app that helps people track their spending, stay within budgets, save for goals and learn basic personal finance. A small set of AI agents works behind it: one categorizes expenses, one watches budgets, one tracks goals, and one answers financial-literacy questions from a curated knowledge base.

Built as a B.Tech Capstone Project (MDM Generative AI), Pimpri Chinchwad College of Engineering, 2026–27. Group G2 / Grp_Cap_17.

## Features

- **Expense logging.** Add expenses by hand, or import a bank CSV or a UPI-app PDF statement. Expenses are categorized automatically (Food, Travel, Shopping, Subscriptions, and so on).
- **Duplicate protection.** Re-uploading a statement does not create double entries.
- **Budgets.** Set a monthly limit per category. The app reports ok, warning (80%+) or over (100%+) and gives a short tip when a budget is at risk.
- **Savings goals.** Set a target and a deadline; the app shows progress and the daily saving needed.
- **Dashboard.** Budget and goal cards, four charts (by category, daily trend, day of week, this month vs last month) and headline insights.
- **Monthly report.** A written summary of the month, generated from the app's own figures.
- **Literacy tutor.** Answers questions such as "what is SIP" or "is UPI safe" using retrieval from an 18-topic knowledge base.
- **Accounts.** Username and password login; each user sees only their own data.

## Architecture

```
Browser (HTML, CSS, JavaScript, Chart.js)
        │  JSON + bearer token
FastAPI service
        ├── Orchestrator
        │     ├── Expense Analyzer  (keyword rules, LLM fallback)
        │     ├── Budget Planner    (usage arithmetic, LLM tip)
        │     ├── Goal Tracker      (pacing arithmetic)
        │     └── Literacy Tutor    (embedding retrieval, LLM answer)
        ├── CSV and PDF importers
        └── SQLite database (every row tagged with user_id)
                │
        Google Gemini API (text generation and embeddings)
```

Calculations are done in ordinary code. The language model is used only for wording, ambiguous merchant names and answers from retrieved text.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, vanilla JavaScript, Chart.js |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Database | SQLite |
| AI | Google Gemini API (text model and `gemini-embedding-001`) |
| Parsing | pdfplumber (PDF), csv (CSV) |
| Security | PBKDF2-HMAC-SHA256 password hashing, session tokens |
| Tests | Python HTTP tests, Node.js + jsdom browser-style tests |

## Project structure

```
capstone-financial-coach/
├── backend/
│   ├── main.py                 API routes
│   ├── auth.py                 Registration, login, sessions
│   ├── database.py             SQLite schema
│   ├── models.py               Request models
│   ├── csv_import.py           CSV parser
│   ├── pdf_import.py           PDF statement parser
│   ├── charts.py               Chart and insight data
│   ├── report_generator.py     Monthly report
│   ├── llm_client.py           Gemini text client
│   ├── vector_store.py         Embeddings and cosine retrieval
│   ├── agents/                 Orchestrator and the four agents
│   ├── evaluation/             Evaluation kit (datasets, runner, README)
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/                    style.css, report_addon.css, auth.css
│   └── js/app.js
└── docs/                       Report and paper (optional)
```

## Setup

Requirements: Python 3.11, a modern browser, and a Gemini API key (free from Google AI Studio). The app runs without a key, but AI-written tips, reports and tutor answers are replaced by a placeholder.

**1. Get the code**

```bash
git clone https://github.com/Arman-19dsa/Capstone-Project.git
cd Capstone-Project
```

**2. Install backend dependencies**

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows (on macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

**3. Add your API key.** Create `backend/.env`:

```
GEMINI_API_KEY=your_key_here
```

This file is git-ignored and must never be committed.

**4. Start the backend**

```bash
python -m uvicorn main:app --reload --port 8000
```

The API documentation is at http://localhost:8000/docs.

**5. Open the frontend.** Open `frontend/index.html` in your browser, or use VS Code's Live Server extension. Register an account on the first screen.

## Using the app

1. **Log Expense:** add one expense, or import a CSV or PDF statement. For a PDF from PhonePe, use History, then Download Statement, and enter the PDF password if the file is protected.
2. **Budgets:** set a monthly limit per category.
3. **Goals:** create a goal, then add savings using the goal's ID shown on the dashboard.
4. **Dashboard:** view budgets, goals, charts and insights; click "Generate This Month's Report" for the written summary.
5. **Literacy Tutor:** ask a question such as "what is an emergency fund".

## Evaluation

The evaluation kit in `backend/evaluation/` measures categorization accuracy, retrieval quality, tutor answers and response times on a labelled dataset. Run it as described in `backend/evaluation/README.txt`:

```bash
python evaluation/run_evaluation.py --dry-run    # free check, no API calls
python evaluation/run_evaluation.py --llm-only   # full run, uses the Gemini free tier
```

## Testing

- Backend: authentication, per-user isolation, PDF parsing and import endpoints (106 checks in total across suites).
- Frontend: browser-style tests against the live backend (login, expenses, import forms, logout, isolation).

## Limitations

- Single installation; SQLite is not suited to many concurrent users.
- No live bank or UPI connection. Statements must be exported and uploaded.
- The knowledge base has 18 entries and covers general personal finance in India. It is not investment, tax or legal advice.
- Only text-based PDF statements are supported, not scans.
- Merchant descriptions that no rule matches, and aggregate figures used in tips and reports, are sent to the Google Gemini API.

## Future work

- Managed database and hosted deployment.
- A reviewer step that checks generated text before it is shown.
- Tutor memory across turns.
- Consent-based bank data through account aggregators.
- Regional-language support.

## Licence and acknowledgement

Academic project. Thanks to Dr. Ashwini Deshpande, project guide.
