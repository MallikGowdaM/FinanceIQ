"""
Loan Risk — Page views.
Views are thin: they call services.py for analytics and return context to templates.
"""
from django.shortcuts import render
from .models import Loan, Borrower


def dashboard(request):
    """Main Loan Risk dashboard page."""
    # Filter params from GET
    risk_filter = request.GET.get("risk_segment", "")
    purpose_filter = request.GET.get("purpose", "")

    loans_qs = Loan.objects.select_related("borrower").all()
    if risk_filter:
        loans_qs = loans_qs.filter(risk_segment=risk_filter)
    if purpose_filter:
        loans_qs = loans_qs.filter(purpose=purpose_filter)

    total = Loan.objects.count()
    defaults = Loan.objects.filter(status="default").count()
    default_rate = round(defaults / max(total, 1) * 100, 1)

    context = {
        "loans": loans_qs[:200],  # table — paginate for prod
        "total_loans": total,
        "default_rate": default_rate,
        "risk_choices": Loan.RISK_CHOICES,
        "purpose_choices": Loan.PURPOSE_CHOICES,
        "active_risk_filter": risk_filter,
        "active_purpose_filter": purpose_filter,
    }
    return render(request, "loan_risk/dashboard.html", context)
