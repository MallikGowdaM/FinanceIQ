"""
Core views — Home page with live KPI summary from all 3 modules.
"""
from django.shortcuts import render

from loan_risk.models import Loan, Borrower
from stock_trends.models import Stock, PriceHistory
from spending.models import Transaction


def home(request):
    """Landing page: top-level KPIs pulled from the database."""
    context = {
        "total_loans": Loan.objects.count(),
        "total_borrowers": Borrower.objects.count(),
        "total_stocks": Stock.objects.count(),
        "total_price_records": PriceHistory.objects.count(),
        "total_transactions": Transaction.objects.count(),
        # Default rate: share of loans with status='default'
        "default_rate": (
            round(
                Loan.objects.filter(status="default").count()
                / max(Loan.objects.count(), 1)
                * 100,
                1,
            )
        ),
    }
    return render(request, "core/home.html", context)
