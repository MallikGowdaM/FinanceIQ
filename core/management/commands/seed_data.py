"""
seed_data management command — loads all CSV datasets into the database.

Usage:
    python manage.py seed_data
    python manage.py seed_data --clear    # clears existing data first (default behavior)
    python manage.py seed_data --no-clear # append without clearing

All data is loaded from data/*.csv files in the project root.
If the CSVs don't exist, they are generated first automatically.
"""
import csv
import os
import sys
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from loan_risk.models import Borrower, Loan
from stock_trends.models import Stock, PriceHistory
from spending.models import Category, Transaction

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_DIR = os.path.join(BASE_DIR, "data")


def csv_path(filename):
    return os.path.join(DATA_DIR, filename)


class Command(BaseCommand):
    help = "Load seed data from CSV files into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-clear",
            action="store_true",
            dest="no_clear",
            help="Do not clear existing data before seeding.",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Finance Dashboard: Seeding Data ===\n"))

        # Generate CSVs if they don't exist
        required = ["borrowers.csv", "loans.csv", "stocks.csv", "price_history.csv", "categories.csv", "transactions.csv"]
        missing = [f for f in required if not os.path.exists(csv_path(f))]
        if missing:
            self.stdout.write(f"  Generating missing CSVs: {', '.join(missing)}")
            # Import and run generator
            sys.path.insert(0, DATA_DIR)
            import generate_seed_data as gen
            borrowers, loans = gen.generate_loans(1000)
            gen.write_csv("borrowers.csv", borrowers[0].keys(), borrowers)
            gen.write_csv("loans.csv", loans[0].keys(), loans)
            stock_rows = [{"ticker": t, "name": n, "sector": s} for t, n, s in gen.STOCKS]
            gen.write_csv("stocks.csv", ["ticker", "name", "sector"], stock_rows)
            price_rows = gen.generate_price_history()
            gen.write_csv("price_history.csv", ["ticker", "date", "open", "high", "low", "close", "volume"], price_rows)
            gen.write_csv("categories.csv", ["name", "budget_limit"], gen.CATEGORIES)
            transactions = gen.generate_transactions(months=24)
            gen.write_csv("transactions.csv", ["id", "date", "description", "amount", "category_name", "type", "payment_method"], transactions)

        if not options["no_clear"]:
            self.stdout.write("  Clearing existing data...")
            Transaction.objects.all().delete()
            Category.objects.all().delete()
            PriceHistory.objects.all().delete()
            Stock.objects.all().delete()
            Loan.objects.all().delete()
            Borrower.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("  [OK] Cleared\n"))

        self._seed_borrowers()
        self._seed_loans()
        self._seed_stocks()
        self._seed_price_history()
        self._seed_categories()
        self._seed_transactions()

        self.stdout.write(self.style.SUCCESS("\n[DONE] Seed data loaded successfully!\n"))

    def _seed_borrowers(self):
        self.stdout.write("  Loading borrowers...")
        path = csv_path("borrowers.csv")
        borrowers = []
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                borrowers.append(
                    Borrower(
                        id=int(row["id"]),
                        age=int(row["age"]),
                        income=float(row["income"]),
                        employment_length=int(row["employment_length"]),
                        credit_score=int(row["credit_score"]),
                        dti_ratio=float(row["dti_ratio"]),
                        home_ownership=row["home_ownership"],
                    )
                )
        Borrower.objects.bulk_create(borrowers, batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"  [OK] Borrowers: {len(borrowers):,}"))

    def _seed_loans(self):
        self.stdout.write("  Loading loans...")
        path = csv_path("loans.csv")
        borrower_map = {b.id: b for b in Borrower.objects.all()}
        loans = []
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                bid = int(row["borrower_id"])
                if bid not in borrower_map:
                    continue
                loans.append(
                    Loan(
                        id=int(row["id"]),
                        borrower=borrower_map[bid],
                        loan_amount=float(row["loan_amount"]),
                        interest_rate=float(row["interest_rate"]),
                        purpose=row["purpose"],
                        issue_date=row["issue_date"],
                        status=row["status"],
                        risk_segment=row["risk_segment"],
                    )
                )
        Loan.objects.bulk_create(loans, batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"  [OK] Loans: {len(loans):,}"))

    def _seed_stocks(self):
        self.stdout.write("  Loading stocks...")
        path = csv_path("stocks.csv")
        stocks = []
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                stocks.append(
                    Stock(ticker=row["ticker"], name=row["name"], sector=row["sector"])
                )
        Stock.objects.bulk_create(stocks, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"  [OK] Stocks: {len(stocks):,}"))

    def _seed_price_history(self):
        self.stdout.write("  Loading price history (this may take a moment)...")
        path = csv_path("price_history.csv")
        stock_map = {s.ticker: s for s in Stock.objects.all()}
        records = []
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ticker = row["ticker"]
                if ticker not in stock_map:
                    continue
                records.append(
                    PriceHistory(
                        stock=stock_map[ticker],
                        date=row["date"],
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=int(row["volume"]),
                    )
                )
        # Bulk insert in batches for memory efficiency
        batch_size = 1000
        for i in range(0, len(records), batch_size):
            PriceHistory.objects.bulk_create(records[i : i + batch_size], ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"  [OK] Price records: {len(records):,}"))

    def _seed_categories(self):
        self.stdout.write("  Loading spending categories...")
        path = csv_path("categories.csv")
        categories = []
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                categories.append(
                    Category(name=row["name"], budget_limit=float(row["budget_limit"]))
                )
        Category.objects.bulk_create(categories, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"  [OK] Categories: {len(categories):,}"))

    def _seed_transactions(self):
        self.stdout.write("  Loading transactions...")
        path = csv_path("transactions.csv")
        cat_map = {c.name: c for c in Category.objects.all()}
        transactions = []
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cat_name = row["category_name"]
                if cat_name not in cat_map:
                    continue
                transactions.append(
                    Transaction(
                        date=row["date"],
                        description=row["description"],
                        amount=float(row["amount"]),
                        category=cat_map[cat_name],
                        type=row["type"],
                        payment_method=row["payment_method"],
                    )
                )
        Transaction.objects.bulk_create(transactions, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f"  [OK] Transactions: {len(transactions):,}"))
