"""
Spending — Unit Tests

Tests cover service layer: budget variance, savings rate,
category breakdown, income-expense trend, and spending leaks.
"""
from datetime import date
from decimal import Decimal

from django.test import TestCase, Client

from .models import Category, Transaction
from .services import (
    category_breakdown,
    budget_vs_actual,
    income_expense_trend,
    spending_kpis,
    spending_leaks,
    available_months,
)


class SpendingServiceTests(TestCase):
    """Test spending analytics service functions."""

    @classmethod
    def setUpTestData(cls):
        """Create categories and transactions for March 2025."""
        cls.food = Category.objects.create(name="Food", budget_limit=Decimal("500.00"))
        cls.rent = Category.objects.create(name="Rent", budget_limit=Decimal("1500.00"))
        cls.income_cat = Category.objects.create(name="Income", budget_limit=Decimal("0.00"))
        cls.entertain = Category.objects.create(name="Entertainment", budget_limit=Decimal("150.00"))

        # Year/month under test
        cls.yr, cls.mo = 2025, 3

        # Income
        Transaction.objects.create(
            date=date(2025, 3, 1), description="Salary", amount=Decimal("4500.00"),
            category=cls.income_cat, type="income", payment_method="bank_transfer"
        )

        # Expenses — Food: $450 (under budget of $500)
        Transaction.objects.create(
            date=date(2025, 3, 5), description="Grocery Store", amount=Decimal("200.00"),
            category=cls.food, type="expense", payment_method="credit_card"
        )
        Transaction.objects.create(
            date=date(2025, 3, 15), description="Restaurant", amount=Decimal("250.00"),
            category=cls.food, type="expense", payment_method="credit_card"
        )

        # Rent: exactly at budget ($1500)
        Transaction.objects.create(
            date=date(2025, 3, 1), description="Rent Payment", amount=Decimal("1500.00"),
            category=cls.rent, type="expense", payment_method="bank_transfer"
        )

        # Entertainment: $200 (OVER budget of $150)
        Transaction.objects.create(
            date=date(2025, 3, 10), description="Cinema", amount=Decimal("50.00"),
            category=cls.entertain, type="expense", payment_method="cash"
        )
        Transaction.objects.create(
            date=date(2025, 3, 20), description="Concert", amount=Decimal("150.00"),
            category=cls.entertain, type="expense", payment_method="credit_card"
        )

        # Small recurring expenses for spending leaks test
        for _ in range(3):
            Transaction.objects.create(
                date=date(2025, 3, 12), description="Coffee Shop", amount=Decimal("5.00"),
                category=cls.food, type="expense", payment_method="upi"
            )

    def test_category_breakdown_sums_correctly(self):
        """category_breakdown should sum all expenses per category."""
        result = category_breakdown(self.yr, self.mo)
        by_cat = {r["category"]: r["amount"] for r in result}

        # Food: 200 + 250 + 3*5 = 465
        self.assertAlmostEqual(by_cat.get("Food", 0), 465.0, places=2)
        # Rent: 1500
        self.assertAlmostEqual(by_cat.get("Rent", 0), 1500.0, places=2)
        # Entertainment: 50 + 150 = 200
        self.assertAlmostEqual(by_cat.get("Entertainment", 0), 200.0, places=2)
        # Income category NOT in expenses
        self.assertNotIn("Income", by_cat)

    def test_budget_vs_actual_variance_signs(self):
        """Overspent categories should have positive variance."""
        result = budget_vs_actual(self.yr, self.mo)
        by_cat = {r["category"]: r for r in result}

        # Entertainment is over budget: variance > 0
        self.assertGreater(by_cat["Entertainment"]["variance"], 0)
        # Food is under budget: variance < 0
        self.assertLess(by_cat["Food"]["variance"], 0)

    def test_savings_rate_calculation(self):
        """
        Income = 4500, Expenses = 465 + 1500 + 200 = 2165
        Net = 2335, Savings Rate = 2335/4500 * 100 ≈ 51.9%
        """
        kpis = spending_kpis(self.yr, self.mo)
        self.assertAlmostEqual(kpis["total_income"], 4500.0, places=2)
        self.assertAlmostEqual(kpis["total_expense"], 2165.0, places=1)
        expected_rate = (4500 - 2165) / 4500 * 100
        self.assertAlmostEqual(kpis["savings_rate"], round(expected_rate, 1), delta=0.5)

    def test_savings_rate_positive(self):
        """When income > expenses, savings rate must be positive."""
        kpis = spending_kpis(self.yr, self.mo)
        self.assertGreater(kpis["savings_rate"], 0)

    def test_biggest_overspend_is_entertainment(self):
        """Entertainment is the only over-budget category."""
        kpis = spending_kpis(self.yr, self.mo)
        self.assertIsNotNone(kpis["biggest_overspend"])
        self.assertEqual(kpis["biggest_overspend"]["category"], "Entertainment")

    def test_income_expense_trend_structure(self):
        """Trend should return a list of {month, income, expense} dicts."""
        result = income_expense_trend(months=12)
        self.assertIsInstance(result, list)
        if result:
            row = result[0]
            self.assertIn("month", row)
            self.assertIn("income", row)
            self.assertIn("expense", row)

    def test_income_expense_trend_includes_march(self):
        """March 2025 data must appear in the 12-month trend."""
        result = income_expense_trend(months=24)
        months = [r["month"] for r in result]
        self.assertIn("2025-03", months)

    def test_spending_leaks_finds_coffee(self):
        """Coffee Shop at $5 × 3 = $15 total should appear as a spending leak."""
        result = spending_leaks(self.yr, self.mo, threshold=50)
        descriptions = [r["description"] for r in result]
        self.assertIn("Coffee Shop", descriptions)
        coffee = next(r for r in result if r["description"] == "Coffee Shop")
        self.assertEqual(coffee["count"], 3)
        self.assertAlmostEqual(coffee["total"], 15.0, places=2)

    def test_available_months_returns_strings(self):
        """available_months should return 'YYYY-MM' formatted strings."""
        result = available_months()
        self.assertIsInstance(result, list)
        if result:
            self.assertRegex(result[0], r"^\d{4}-\d{2}$")

    def test_zero_income_savings_rate(self):
        """savings_rate should return 0 (not crash) when income is 0."""
        kpis = spending_kpis(2000, 1)  # month with no data
        self.assertEqual(kpis["savings_rate"], 0.0)


class SpendingAPITests(TestCase):
    """Smoke tests for spending API endpoints."""

    def setUp(self):
        self.client = Client()

    def test_category_breakdown_endpoint(self):
        resp = self.client.get("/api/spending/category-breakdown/?month=2025-03")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_budget_vs_actual_endpoint(self):
        resp = self.client.get("/api/spending/budget-vs-actual/?month=2025-03")
        self.assertEqual(resp.status_code, 200)

    def test_income_expense_trend_endpoint(self):
        resp = self.client.get("/api/spending/income-expense-trend/")
        self.assertEqual(resp.status_code, 200)

    def test_kpis_endpoint(self):
        resp = self.client.get("/api/spending/kpis/?month=2025-03")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("savings_rate", data)
        self.assertIn("total_income", data)

    def test_available_months_endpoint(self):
        resp = self.client.get("/api/spending/available-months/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)
