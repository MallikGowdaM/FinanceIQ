"""
Spending — Service Layer

All analytics logic for the personal finance module.
Computes budget variance, savings rate, spending leaks, trend data.
"""
from datetime import date
from decimal import Decimal

import pandas as pd
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth

from .models import Category, Transaction


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _tx_df(year: int, month: int) -> pd.DataFrame:
    """Load all transactions for a given month into a DataFrame."""
    qs = Transaction.objects.filter(
        date__year=year, date__month=month
    ).select_related("category").values(
        "id", "date", "description", "amount", "type",
        "payment_method", "category__name", "category__budget_limit"
    )
    df = pd.DataFrame(list(qs))
    if not df.empty:
        df = df.rename(columns={
            "category__name": "category",
            "category__budget_limit": "budget_limit",
        })
        df["amount"] = df["amount"].astype(float)
        df["budget_limit"] = df["budget_limit"].astype(float)
        df["date"] = pd.to_datetime(df["date"])
    return df


# ─── Analytics Functions ──────────────────────────────────────────────────────

def category_breakdown(year: int, month: int) -> list[dict]:
    """
    Return total spend per category for a given month.
    Income transactions are excluded (type='expense' only).

    Returns: [{"category": "Food", "amount": 450.0}, ...]
    """
    qs = (
        Transaction.objects.filter(date__year=year, date__month=month, type="expense")
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    return [
        {"category": row["category__name"], "amount": round(float(row["total"] or 0), 2)}
        for row in qs
    ]


def budget_vs_actual(year: int, month: int) -> list[dict]:
    """
    Compare budget_limit vs actual spend per expense category.
    Variance = actual - budget (positive = overspent).

    Returns: [{"category": "Food", "budget": 500.0, "actual": 450.0, "variance": -50.0}, ...]
    """
    categories = Category.objects.all()
    result = []
    for cat in categories:
        # Sum expenses in this category for the month
        actual = Transaction.objects.filter(
            date__year=year,
            date__month=month,
            category=cat,
            type="expense",
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        actual = float(actual)
        budget = float(cat.budget_limit)
        # Skip income categories (budget_limit == 0) unless they have actual spend
        if budget == 0 and actual == 0:
            continue
        result.append({
            "category": cat.name,
            "budget": budget,
            "actual": round(actual, 2),
            "variance": round(actual - budget, 2),
        })
    result.sort(key=lambda x: x["variance"], reverse=True)
    return result


def income_expense_trend(months: int = 12) -> list[dict]:
    """
    Return monthly income and expense totals for the last `months` months.
    Used for the trend line chart.

    Returns: [{"month": "2025-08", "income": 4500.0, "expense": 3200.0}, ...]
    """
    qs = (
        Transaction.objects
        .annotate(month=TruncMonth("date"))
        .values("month", "type")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    # Pivot into {month: {income: X, expense: Y}}
    monthly: dict[str, dict] = {}
    for row in qs:
        key = row["month"].strftime("%Y-%m")
        if key not in monthly:
            monthly[key] = {"income": 0.0, "expense": 0.0}
        monthly[key][row["type"]] = round(float(row["total"] or 0), 2)

    # Return only last `months` entries sorted by date
    sorted_months = sorted(monthly.keys())[-months:]
    return [
        {"month": m, "income": monthly[m]["income"], "expense": monthly[m]["expense"]}
        for m in sorted_months
    ]


def spending_kpis(year: int, month: int) -> dict:
    """
    Return key metrics for the selected month:
    - savings_rate: (income - expenses) / income × 100
    - biggest_overspend: category name + overage amount
    - total_income, total_expense, net

    Returns: {"savings_rate": 28.5, "biggest_overspend": {"category": "Shopping", "overage": 150.0}, ...}
    """
    income = Transaction.objects.filter(
        date__year=year, date__month=month, type="income"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    expense = Transaction.objects.filter(
        date__year=year, date__month=month, type="expense"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    income = float(income)
    expense = float(expense)
    net = income - expense
    savings_rate = round(net / income * 100, 1) if income > 0 else 0.0

    # Biggest overspend = category with highest positive variance (actual > budget)
    bva = budget_vs_actual(year, month)
    overspends = [x for x in bva if x["variance"] > 0]
    biggest_overspend = overspends[0] if overspends else None

    return {
        "total_income": round(income, 2),
        "total_expense": round(expense, 2),
        "net": round(net, 2),
        "savings_rate": savings_rate,
        "biggest_overspend": biggest_overspend,
    }


def spending_leaks(year: int, month: int, threshold: float = 50.0) -> list[dict]:
    """
    Find "spending leaks" — small recurring expense descriptions whose
    individual amounts are below the threshold but whose monthly total is significant.

    Strategy: group by description, filter where individual amount < threshold,
    sort by monthly total descending. These are subscriptions, snacks, etc. that
    quietly drain the budget.

    Returns: [{"description": "Netflix", "count": 1, "total": 15.99}, ...]
    """
    df = _tx_df(year, month)
    if df.empty or "type" not in df.columns:
        return []

    expenses = df[df["type"] == "expense"]
    # Only look at transactions individually below the threshold
    small = expenses[expenses["amount"] < threshold]
    if small.empty:
        return []

    grouped = (
        small.groupby("description")
        .agg(count=("amount", "count"), total=("amount", "sum"))
        .reset_index()
        .sort_values("total", ascending=False)
        .head(10)
    )
    return [
        {
            "description": row["description"],
            "count": int(row["count"]),
            "total": round(float(row["total"]), 2),
        }
        for _, row in grouped.iterrows()
    ]


def available_months() -> list[str]:
    """
    Return all 'YYYY-MM' strings that have at least one transaction.
    Used to populate the month selector dropdown.
    """
    qs = (
        Transaction.objects
        .annotate(month=TruncMonth("date"))
        .values_list("month", flat=True)
        .distinct()
        .order_by("month")
    )
    return [m.strftime("%Y-%m") for m in qs if m]
