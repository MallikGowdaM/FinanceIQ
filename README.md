# FinanceIQ — Full-Stack Finance Analytics Dashboard

A portfolio-ready full-stack web application combining three finance analytics modules into a single, cohesive dashboard. Built to demonstrate both full-stack development skills (Django, REST API, SQL) and data analytics skills (EDA, statistics, interactive visualisation).

> **Disclaimer:** All data is synthetic and for demonstration purposes only. This is not financial or investment advice.

---

## Architecture Overview

```
Browser (HTML/CSS/JS + Chart.js)
        │
        │  fetch() → JSON
        ▼
Django REST Framework API  (/api/*)
        │
        │  calls
        ▼
Service Layer (pandas, numpy, scipy, scikit-learn)
        │
        │  Django ORM
        ▼
SQLite / PostgreSQL Database
```

```
finance-dashboard/
├── finance_dashboard/      ← Django project (settings, urls, wsgi)
├── core/                   ← Home page + seed_data management command
│   └── management/commands/seed_data.py
├── loan_risk/              ← Loan Default Risk module
│   ├── models.py           (Borrower, Loan)
│   ├── services.py         (risk scoring, EDA aggregations, point-biserial corr)
│   ├── api_views.py        (DRF views)
│   └── tests.py
├── stock_trends/           ← Stock Market Trends module
│   ├── models.py           (Stock, PriceHistory)
│   ├── services.py         (GBM returns, rolling vol, MA, correlation)
│   ├── api_views.py
│   └── tests.py
├── spending/               ← Personal Finance module
│   ├── models.py           (Category, Transaction)
│   ├── services.py         (budget variance, savings rate, spending leaks)
│   ├── api_views.py
│   └── tests.py
├── templates/              ← Shared base.html + per-app dashboards
├── static/
│   ├── css/main.css        ← Dark-theme design system (CSS custom properties)
│   └── js/charts.js        ← Chart.js factory helpers + heatmap renderer
├── data/
│   └── generate_seed_data.py
├── manage.py
├── requirements.txt
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.9+, Django 5.2, Django REST Framework 3.16 |
| Analytics | pandas 3.x, numpy 2.x, scipy 1.x, scikit-learn 1.x |
| Database | SQLite (local dev) / PostgreSQL (production) |
| Frontend | HTML5, Bootstrap 5, Vanilla JS (no React) |
| Charts | Chart.js 4.x (bar, line, scatter, doughnut + custom heatmap) |
| Config | django-environ / .env |

---

## Modules

### 1. Loan Default Risk (`/loan-risk/`)
- Filterable loan table (filter by risk segment, purpose)
- Charts: default rate by credit score band, DTI ratio buckets, risk distribution pie, income vs loan scatter
- Risk drivers panel (point-biserial correlation of features vs default)
- **Instant risk scoring form** — enter borrower details → see Low/Medium/High risk result via API

### 2. Stock Market Trends (`/stock-trends/`)
- Ticker multi-select pill UI (10 tickers: AAPL, MSFT, GOOGL, AMZN, META, TSLA, NVDA, JPM, JNJ, XOM)
- Date range selector (6M / 1Y / 3Y / ALL)
- Charts: normalised price comparison, rolling 20-day volatility, MA crossover (MA20/50/200), risk-return scatter
- Correlation heatmap (Pearson correlation of daily returns)

### 3. Personal Finance (`/spending/`)
- Month/year selector with available-months indicator
- KPI cards: total income, expenses, net savings, savings rate
- Charts: income-expense trend (12 months), category spend pie, budget vs actual, spending leaks table
- **Add transaction form** — AJAX POST, refreshes charts immediately

---

## Setup Instructions

### Prerequisites
- Python 3.9 or higher

### 1. Clone & create virtual environment
```bash
git clone https://github.com/YOUR_USERNAME/finance-dashboard.git
cd finance-dashboard
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
copy .env.example .env      # Windows
cp .env.example .env        # macOS/Linux
# Edit .env if needed (default settings work out-of-the-box with SQLite)
```

### 4. Run migrations
```bash
python manage.py migrate
```

### 5. Seed the database
```bash
python manage.py seed_data
```
This auto-generates all CSV datasets (if missing) and loads them:
- 1,000 borrowers + loans
- 10 stocks + ~9,000 daily OHLCV records (3 years, GBM simulation)
- 8 spending categories + ~1,200 transactions (24 months)

### 6. Create admin superuser (optional)
```bash
python manage.py createsuperuser
```

### 7. Run the development server
```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/** in your browser.

---

## Running Tests
```bash
python manage.py test loan_risk stock_trends spending
```
**44 tests** covering:
- Risk segment boundary conditions (Low/Medium/High scoring logic)
- Analytics function outputs (default rates, budget variance, savings rate formula)
- Statistical correctness (correlation matrix symmetry, diagonal = 1, volatility ≥ 0)
- API endpoint smoke tests (200 status, correct JSON structure)

---

## API Endpoints

All endpoints return JSON. No authentication required (portfolio demo).

### Loan Risk (`/api/loan-risk/`)
| Method | Path | Description |
|---|---|---|
| GET | `/default-by-credit-band/` | Default rate per FICO band |
| GET | `/default-by-dti/` | Default rate per DTI bucket |
| GET | `/risk-distribution/` | Loan count per risk segment |
| GET | `/scatter/` | Income vs loan amount sample |
| GET | `/risk-drivers/` | Point-biserial correlations |
| GET | `/summary/` | Overall KPI metrics |
| POST | `/predict/` | Instant risk segment for new borrower |

### Stock Trends (`/api/stock-trends/`)
| Method | Path | Query Params | Description |
|---|---|---|---|
| GET | `/tickers/` | — | All tracked stocks |
| GET | `/normalized-prices/` | `tickers`, `range` | Base-100 normalised close |
| GET | `/volatility/` | `tickers`, `range` | 20-day rolling vol (annualised) |
| GET | `/moving-averages/` | `tickers`, `range` | Close + MA20/50/200 |
| GET | `/correlation/` | `tickers`, `range` | Pearson correlation matrix |
| GET | `/risk-return/` | `range` | Ann. return vs volatility |

### Spending (`/api/spending/`)
| Method | Path | Query Params | Description |
|---|---|---|---|
| GET | `/category-breakdown/` | `month` (YYYY-MM) | Spend per category |
| GET | `/budget-vs-actual/` | `month` | Budget vs actual variance |
| GET | `/income-expense-trend/` | `months` | Monthly trend (12m default) |
| GET | `/kpis/` | `month` | Savings rate + overspend |
| GET | `/spending-leaks/` | `month`, `threshold` | Small recurring transactions |
| GET | `/available-months/` | — | Months with data |
| POST | `/transactions/` | — | Add new transaction |

---

## Data Generation

Stock prices use **Geometric Brownian Motion** (GBM) — the industry-standard model for equity price simulation:

```
S(t+dt) = S(t) × exp((μ - σ²/2)dt + σ√dt × Z)
```

where Z ~ N(0,1), dt = 1/252 trading day, μ = annual drift, σ = annual volatility.

Loan data uses realistic distributions:
- Credit scores: N(680, 90), clipped to [300, 850]
- Income: log-normal, median ~$55k
- DTI: N(22, 10), clipped to [1, 60]
- Default rate: ~20% (higher for high-risk segments)

---

## Deployment

### Render / Railway
1. Set `DATABASE_URL` to a PostgreSQL connection string in environment variables
2. Set `DEBUG=False` and `SECRET_KEY` to a strong random value
3. Add a build command: `pip install -r requirements.txt && python manage.py migrate && python manage.py seed_data`
4. Start command: `gunicorn finance_dashboard.wsgi`
5. Add `gunicorn` to `requirements.txt`

### PythonAnywhere
1. Upload project files via `git clone` in the Bash console
2. Create a virtual environment and install requirements
3. Configure the WSGI file to point to `finance_dashboard.wsgi`
4. Set environment variables in the web app dashboard
5. Run `python manage.py migrate` and `python manage.py seed_data`

### Static Files (Production)
```bash
python manage.py collectstatic
```
Configure your web server (Nginx/Caddy) to serve `staticfiles/`.

---

## What This Demonstrates

### Full-Stack Development
- **Django 5** project structure: multiple apps, service layer, admin, migrations
- **Django REST Framework** API with proper error handling and JSON responses
- **Vanilla JS** fetch API integration — no React, demonstrating core JS skills
- **Bootstrap 5** with a custom dark-theme design system (CSS custom properties)
- **Chart.js 4** with a reusable factory pattern (bar, line, scatter, doughnut, heatmap)

### Data Analytics & Statistics
- **Exploratory Data Analysis** — default rates by credit band, DTI, risk segment
- **Point-biserial correlation** — identifying which features most strongly predict default
- **Geometric Brownian Motion** — industry-standard equity price simulation
- **Financial metrics** — normalised returns, rolling volatility (σ√252), Pearson correlation, annualised return
- **Personal finance analytics** — budget variance, savings rate, spending leak detection

### Software Engineering
- **Separation of concerns**: models → services → views → templates
- **Bulk database operations** (bulk_create with batching for 9k+ records)
- **44 unit tests** covering business logic and API endpoints
- **Idempotent seed command** (safe to re-run)
- **Responsive design** — works on desktop and tablet
