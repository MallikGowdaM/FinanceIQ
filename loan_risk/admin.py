"""
Loan Risk — Django Admin registration.
Makes borrowers and loans easily manageable from /admin/.
"""
from django.contrib import admin
from .models import Borrower, Loan


@admin.register(Borrower)
class BorrowerAdmin(admin.ModelAdmin):
    list_display = ["id", "age", "income", "credit_score", "dti_ratio", "home_ownership", "employment_length"]
    list_filter = ["home_ownership"]
    search_fields = ["id"]
    ordering = ["-id"]


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ["id", "borrower", "loan_amount", "interest_rate", "purpose", "status", "risk_segment", "issue_date"]
    list_filter = ["status", "risk_segment", "purpose"]
    search_fields = ["borrower__id"]
    ordering = ["-issue_date"]
    readonly_fields = ["risk_segment"]
