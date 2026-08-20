"""
Spending — DRF API Views.
Each view calls services.py and returns clean JSON to the frontend.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status
from datetime import date

from . import services
from .models import Category, Transaction


def _parse_month(month_str):
    """Parse 'YYYY-MM' string, default to current month on failure."""
    try:
        year, month = map(int, month_str.split("-"))
        return year, month
    except (ValueError, AttributeError, TypeError):
        today = date.today()
        return today.year, today.month


class CategoryBreakdownView(APIView):
    """GET /api/spending/category-breakdown/?month=2026-06"""
    def get(self, request):
        year, month = _parse_month(request.query_params.get("month"))
        data = services.category_breakdown(year, month)
        return Response(data)


class BudgetVsActualView(APIView):
    """GET /api/spending/budget-vs-actual/?month=2026-06"""
    def get(self, request):
        year, month = _parse_month(request.query_params.get("month"))
        data = services.budget_vs_actual(year, month)
        return Response(data)


class IncomeExpenseTrendView(APIView):
    """GET /api/spending/income-expense-trend/"""
    def get(self, request):
        months = int(request.query_params.get("months", 12))
        data = services.income_expense_trend(months)
        return Response(data)


class SpendingKPIsView(APIView):
    """GET /api/spending/kpis/?month=2026-06"""
    def get(self, request):
        year, month = _parse_month(request.query_params.get("month"))
        data = services.spending_kpis(year, month)
        return Response(data)


class SpendingLeaksView(APIView):
    """GET /api/spending/spending-leaks/?month=2026-06"""
    def get(self, request):
        year, month = _parse_month(request.query_params.get("month"))
        threshold = float(request.query_params.get("threshold", 50))
        data = services.spending_leaks(year, month, threshold)
        return Response(data)


class TransactionCreateView(APIView):
    """POST /api/spending/transactions/
    Body: {date, description, amount, category_name, type, payment_method}
    """
    def post(self, request):
        d = request.data
        try:
            category = Category.objects.get(name=d.get("category_name"))
        except Category.DoesNotExist:
            return Response(
                {"error": f"Category '{d.get('category_name')}' not found."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )
        try:
            tx = Transaction.objects.create(
                date=d["date"],
                description=d.get("description", ""),
                amount=float(d["amount"]),
                category=category,
                type=d.get("type", "expense"),
                payment_method=d.get("payment_method", "credit_card"),
            )
            return Response(
                {
                    "id": tx.id,
                    "date": str(tx.date),
                    "description": tx.description,
                    "amount": float(tx.amount),
                    "category": tx.category.name,
                    "type": tx.type,
                },
                status=drf_status.HTTP_201_CREATED,
            )
        except (KeyError, ValueError) as e:
            return Response({"error": str(e)}, status=drf_status.HTTP_400_BAD_REQUEST)


class AvailableMonthsView(APIView):
    """GET /api/spending/available-months/
    Returns a list of 'YYYY-MM' strings with transaction data.
    """
    def get(self, request):
        data = services.available_months()
        return Response(data)
