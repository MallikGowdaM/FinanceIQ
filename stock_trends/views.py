"""
Stock Trends — Page views.
"""
from django.shortcuts import render
from .models import Stock


def dashboard(request):
    """Main Stock Trends dashboard page."""
    tickers = list(Stock.objects.values_list("ticker", flat=True))
    context = {
        "tickers": tickers,
        "default_tickers": ["AAPL", "MSFT", "GOOGL"],
    }
    return render(request, "stock_trends/dashboard.html", context)
