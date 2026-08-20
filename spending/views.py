"""
Spending — Page views.
"""
from datetime import date
from django.shortcuts import render
from .models import Category, Transaction


def dashboard(request):
    """Main Spending dashboard page."""
    today = date.today()
    # Default to current month; allow ?month=YYYY-MM override
    month_str = request.GET.get("month", today.strftime("%Y-%m"))
    try:
        year, month = map(int, month_str.split("-"))
    except (ValueError, AttributeError):
        year, month = today.year, today.month
        month_str = f"{year:04d}-{month:02d}"

    categories = list(Category.objects.values_list("name", flat=True))

    context = {
        "selected_month": month_str,
        "categories": categories,
        "current_year": year,
        "current_month": month,
        "payment_method_choices": Transaction.PAYMENT_METHOD_CHOICES,
        "type_choices": Transaction.TYPE_CHOICES,
    }
    return render(request, "spending/dashboard.html", context)
