"""
generate_seed_data.py — Generates realistic synthetic CSV datasets for seeding.

Run directly:   python data/generate_seed_data.py
Output files:   data/loans.csv, data/stocks.csv, data/price_history.csv, data/transactions.csv

Design choices:
- Loan data uses realistic credit score / DTI / income distributions (~20% default rate)
- Stock prices use Geometric Brownian Motion (GBM) — the standard model for equity prices
- Spending data covers 24 months across 8 realistic personal finance categories
"""
import math
import random
import csv
import os
from datetime import date, timedelta

# Reproducible seed for consistent test data
random.seed(42)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ─── Loan Data ────────────────────────────────────────────────────────────────

def generate_loans(n=1000):
    """
    Generate n synthetic borrower + loan records.

    Distributions calibrated to approximate real lending data:
    - Credit scores: roughly normal around 680, clipped to [300, 850]
    - Income: log-normal, median ~$55k, right-skewed
    - DTI: beta-distributed around 20-30%
    - Default rate: ~20%, higher for High risk borrowers
    """
    home_ownerships = ["RENT", "OWN", "MORTGAGE", "OTHER"]
    purposes = [
        "debt_consolidation", "home_improvement", "medical",
        "small_business", "education", "major_purchase", "car", "other"
    ]

    borrowers = []
    loans = []

    start_date = date(2020, 1, 1)
    end_date = date(2024, 12, 31)
    date_range = (end_date - start_date).days

    for i in range(1, n + 1):
        # Borrower attributes
        credit_score = int(min(850, max(300, random.gauss(680, 90))))
        income = max(15000, int(math.exp(random.gauss(10.9, 0.5))))  # log-normal
        employment_length = random.randint(0, 30)
        age = random.randint(22, 70)
        dti = round(max(1, min(60, random.gauss(22, 10))), 1)
        home_ownership = random.choices(
            home_ownerships, weights=[40, 15, 40, 5]
        )[0]

        # Loan attributes
        loan_amount = random.randint(1000, 40000)
        interest_rate = round(max(4, min(30, random.gauss(12, 4))), 2)
        purpose = random.choices(
            purposes, weights=[30, 12, 8, 8, 8, 10, 9, 15]
        )[0]
        issue_date = start_date + timedelta(days=random.randint(0, date_range))

        # Risk score (simplified version matching services.py logic)
        risk_points = 0
        if credit_score < 580:
            risk_points += 3
        elif credit_score < 670:
            risk_points += 2
        elif credit_score < 740:
            risk_points += 1
        if dti > 40:
            risk_points += 3
        elif dti > 30:
            risk_points += 2
        elif dti > 20:
            risk_points += 1
        lti = loan_amount / max(income, 1)
        if lti > 5:
            risk_points += 2
        elif lti > 2.5:
            risk_points += 1

        if risk_points >= 5:
            risk_segment = "High"
        elif risk_points >= 3:
            risk_segment = "Medium"
        else:
            risk_segment = "Low"

        # Default probability: higher for high-risk, lower for low-risk
        default_probs = {"Low": 0.06, "Medium": 0.18, "High": 0.38}
        rand_val = random.random()
        if rand_val < default_probs[risk_segment]:
            loan_status = "default"
        elif rand_val < default_probs[risk_segment] + 0.3:
            loan_status = "paid"
        else:
            loan_status = "current"

        borrowers.append({
            "id": i,
            "age": age,
            "income": income,
            "employment_length": employment_length,
            "credit_score": credit_score,
            "dti_ratio": dti,
            "home_ownership": home_ownership,
        })
        loans.append({
            "id": i,
            "borrower_id": i,
            "loan_amount": loan_amount,
            "interest_rate": interest_rate,
            "purpose": purpose,
            "issue_date": issue_date.strftime("%Y-%m-%d"),
            "status": loan_status,
            "risk_segment": risk_segment,
        })

    return borrowers, loans


# ─── Stock Data ───────────────────────────────────────────────────────────────

STOCKS = [
    ("AAPL", "Apple Inc.", "Technology"),
    ("MSFT", "Microsoft Corp.", "Technology"),
    ("GOOGL", "Alphabet Inc.", "Communication Services"),
    ("AMZN", "Amazon.com Inc.", "Consumer Discretionary"),
    ("META", "Meta Platforms Inc.", "Communication Services"),
    ("TSLA", "Tesla Inc.", "Consumer Discretionary"),
    ("NVDA", "NVIDIA Corp.", "Technology"),
    ("JPM", "JPMorgan Chase & Co.", "Financials"),
    ("JNJ", "Johnson & Johnson", "Healthcare"),
    ("XOM", "Exxon Mobil Corp.", "Energy"),
]

# Approximate starting prices and annual drift/volatility for each ticker
TICKER_PARAMS = {
    "AAPL": {"start": 150.0, "drift": 0.20, "vol": 0.25},
    "MSFT": {"start": 260.0, "drift": 0.18, "vol": 0.22},
    "GOOGL": {"start": 120.0, "drift": 0.15, "vol": 0.24},
    "AMZN": {"start": 100.0, "drift": 0.16, "vol": 0.28},
    "META": {"start": 200.0, "drift": 0.22, "vol": 0.35},
    "TSLA": {"start": 200.0, "drift": 0.10, "vol": 0.55},
    "NVDA": {"start": 250.0, "drift": 0.45, "vol": 0.50},
    "JPM":  {"start": 140.0, "drift": 0.12, "vol": 0.20},
    "JNJ":  {"start": 160.0, "drift": 0.05, "vol": 0.15},
    "XOM":  {"start": 70.0,  "drift": 0.08, "vol": 0.22},
}


def generate_price_history(start_date=date(2022, 1, 3), end_date=date(2025, 6, 30)):
    """
    Generate daily OHLCV data for all 10 tickers using Geometric Brownian Motion.

    GBM: S(t+dt) = S(t) * exp((μ - σ²/2)*dt + σ*√dt*Z)
    where Z ~ N(0,1), dt = 1/252 (one trading day)

    OHLC are synthesised from the close price with realistic intraday range.
    Volume is generated with log-normal distribution.
    """
    rows = []
    dt = 1 / 252  # one trading day as fraction of year

    # Generate all weekdays in the range
    trading_days = []
    d = start_date
    while d <= end_date:
        if d.weekday() < 5:  # Monday–Friday
            trading_days.append(d)
        d += timedelta(days=1)

    for ticker, params in TICKER_PARAMS.items():
        price = params["start"]
        mu = params["drift"]
        sigma = params["vol"]

        for day in trading_days:
            # GBM step
            z = random.gauss(0, 1)
            price = price * math.exp((mu - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z)
            price = max(1.0, price)  # floor at $1

            # Synthesise intraday OHLC from close price
            daily_range = price * sigma * math.sqrt(dt) * 2
            high = round(price + random.uniform(0, daily_range), 4)
            low = round(max(0.01, price - random.uniform(0, daily_range)), 4)
            open_price = round(low + random.uniform(0, high - low), 4)
            close = round(price, 4)

            # Volume: log-normal, roughly 10M–100M shares
            volume = int(math.exp(random.gauss(16.5, 0.8)))

            rows.append({
                "ticker": ticker,
                "date": day.strftime("%Y-%m-%d"),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            })

    return rows


# ─── Spending / Transaction Data ──────────────────────────────────────────────

CATEGORIES = [
    {"name": "Housing", "budget_limit": 1500.00},
    {"name": "Food & Dining", "budget_limit": 500.00},
    {"name": "Transport", "budget_limit": 250.00},
    {"name": "Entertainment", "budget_limit": 150.00},
    {"name": "Health & Fitness", "budget_limit": 200.00},
    {"name": "Shopping", "budget_limit": 300.00},
    {"name": "Utilities", "budget_limit": 120.00},
    {"name": "Income", "budget_limit": 0.00},
]

EXPENSE_TEMPLATES = {
    "Housing": [
        ("Rent Payment", 1350, 1550),
    ],
    "Food & Dining": [
        ("Grocery Store", 60, 120),
        ("Restaurant", 20, 80),
        ("Coffee Shop", 5, 15),
        ("Food Delivery", 25, 60),
        ("Bakery", 8, 20),
    ],
    "Transport": [
        ("Fuel / Petrol", 40, 80),
        ("Uber / Lyft", 12, 35),
        ("Metro / Bus Pass", 30, 60),
        ("Car Maintenance", 80, 300),
        ("Parking", 5, 25),
    ],
    "Entertainment": [
        ("Netflix", 15.99, 15.99),
        ("Spotify", 9.99, 9.99),
        ("Cinema Tickets", 20, 50),
        ("Gaming / Steam", 10, 60),
        ("Concert / Events", 40, 150),
    ],
    "Health & Fitness": [
        ("Gym Membership", 40, 70),
        ("Pharmacy", 15, 50),
        ("Doctor Visit", 40, 150),
        ("Health Insurance", 120, 200),
    ],
    "Shopping": [
        ("Amazon Purchase", 15, 120),
        ("Clothing Store", 30, 150),
        ("Electronics", 50, 400),
        ("Home Goods", 20, 100),
        ("Books / Stationery", 10, 40),
    ],
    "Utilities": [
        ("Electricity Bill", 50, 100),
        ("Internet Bill", 40, 70),
        ("Water Bill", 20, 40),
        ("Mobile Phone Bill", 25, 60),
    ],
}

INCOME_TEMPLATES = [
    ("Monthly Salary", 4000, 5500),
    ("Freelance Income", 200, 1500),
    ("Dividend Income", 50, 300),
]


def generate_transactions(months=24):
    """
    Generate realistic personal finance transactions for the last `months` months.
    Includes:
    - Monthly salary (always)
    - Occasional freelance / dividend income
    - Regular recurring expenses (rent, subscriptions)
    - Variable daily expenses with realistic randomness
    """
    transactions = []
    tx_id = 1

    today = date.today()
    # Start from `months` ago
    start = date(today.year, today.month, 1)
    for _ in range(months):
        if start.month == 1:
            start = date(start.year - 1, 12, 1)
        else:
            start = date(start.year, start.month - 1, 1)

    current = start

    payment_methods = ["credit_card", "debit_card", "bank_transfer", "upi", "cash"]
    pm_weights = [35, 25, 20, 15, 5]

    while current <= today:
        year, month = current.year, current.month

        # ── Income ──────────────────────────────────────────
        # Salary: on the 1st of each month
        salary = round(random.uniform(4200, 5000), 2)
        transactions.append({
            "id": tx_id,
            "date": date(year, month, 1).strftime("%Y-%m-%d"),
            "description": "Monthly Salary",
            "amount": salary,
            "category_name": "Income",
            "type": "income",
            "payment_method": "bank_transfer",
        })
        tx_id += 1

        # Occasional freelance income (40% chance per month)
        if random.random() < 0.40:
            freelance = round(random.uniform(300, 1200), 2)
            day = random.randint(10, 25)
            transactions.append({
                "id": tx_id,
                "date": date(year, month, day).strftime("%Y-%m-%d"),
                "description": "Freelance Income",
                "amount": freelance,
                "category_name": "Income",
                "type": "income",
                "payment_method": "bank_transfer",
            })
            tx_id += 1

        # ── Expenses ─────────────────────────────────────────
        for category, templates in EXPENSE_TEMPLATES.items():
            for description, min_amt, max_amt in templates:
                # Determine frequency per month
                if description in ("Rent Payment", "Electricity Bill", "Internet Bill",
                                   "Water Bill", "Mobile Phone Bill", "Netflix", "Spotify",
                                   "Gym Membership", "Health Insurance", "Metro / Bus Pass"):
                    # Fixed monthly — always once
                    occurrences = 1
                else:
                    # Variable — random occurrences 1–5 times per month
                    occurrences = random.randint(1, 5 if category == "Food & Dining" else 2)

                for _ in range(occurrences):
                    amount = round(random.uniform(min_amt, max_amt), 2)
                    # Add ±10% noise
                    noise_factor = random.uniform(0.90, 1.10)
                    amount = round(amount * noise_factor, 2)
                    day = random.randint(1, 28)
                    pm = random.choices(payment_methods, weights=pm_weights)[0]
                    transactions.append({
                        "id": tx_id,
                        "date": date(year, month, day).strftime("%Y-%m-%d"),
                        "description": description,
                        "amount": amount,
                        "category_name": category,
                        "type": "expense",
                        "payment_method": pm,
                    })
                    tx_id += 1

        # Move to next month
        if month == 12:
            current = date(year + 1, 1, 1)
        else:
            current = date(year, month + 1, 1)

    return transactions


# ─── Main ─────────────────────────────────────────────────────────────────────

def write_csv(filename, fieldnames, rows):
    path = os.path.join(BASE_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  [OK] {filename}: {len(rows):,} rows")


if __name__ == "__main__":
    print("Generating seed data...")

    # Loans
    borrowers, loans = generate_loans(1000)
    write_csv("borrowers.csv", borrowers[0].keys(), borrowers)
    write_csv("loans.csv", loans[0].keys(), loans)

    # Stocks metadata
    stock_rows = [{"ticker": t, "name": n, "sector": s} for t, n, s in STOCKS]
    write_csv("stocks.csv", ["ticker", "name", "sector"], stock_rows)

    # Price history (GBM)
    price_rows = generate_price_history()
    write_csv("price_history.csv", ["ticker", "date", "open", "high", "low", "close", "volume"], price_rows)

    # Spending categories + transactions
    write_csv("categories.csv", ["name", "budget_limit"], CATEGORIES)
    transactions = generate_transactions(months=24)
    write_csv("transactions.csv", ["id", "date", "description", "amount", "category_name", "type", "payment_method"], transactions)

    print(f"\nDone! Files saved to {BASE_DIR}/")
