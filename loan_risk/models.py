"""
Loan Risk — Data Models

Borrower: demographic and financial profile of a loan applicant.
Loan: a single loan tied to a borrower, with status and risk segment.
"""
from django.db import models


class Borrower(models.Model):
    HOME_OWNERSHIP_CHOICES = [
        ("RENT", "Rent"),
        ("OWN", "Own"),
        ("MORTGAGE", "Mortgage"),
        ("OTHER", "Other"),
    ]

    age = models.PositiveIntegerField()
    income = models.DecimalField(max_digits=12, decimal_places=2)
    employment_length = models.PositiveIntegerField(help_text="Years employed")
    credit_score = models.PositiveIntegerField(
        help_text="FICO-style score 300–850"
    )
    dti_ratio = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Debt-to-income ratio as a percentage",
    )
    home_ownership = models.CharField(
        max_length=10, choices=HOME_OWNERSHIP_CHOICES, default="RENT"
    )

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["credit_score"]),
            models.Index(fields=["dti_ratio"]),
        ]

    def __str__(self):
        return f"Borrower #{self.id} | Credit: {self.credit_score} | Income: {self.income}"


class Loan(models.Model):
    STATUS_CHOICES = [
        ("current", "Current"),
        ("paid", "Paid"),
        ("default", "Default"),
    ]
    RISK_CHOICES = [
        ("Low", "Low"),
        ("Medium", "Medium"),
        ("High", "High"),
    ]
    PURPOSE_CHOICES = [
        ("debt_consolidation", "Debt Consolidation"),
        ("home_improvement", "Home Improvement"),
        ("medical", "Medical"),
        ("small_business", "Small Business"),
        ("education", "Education"),
        ("major_purchase", "Major Purchase"),
        ("car", "Car"),
        ("other", "Other"),
    ]

    borrower = models.ForeignKey(
        Borrower, on_delete=models.CASCADE, related_name="loans"
    )
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Annual interest rate %"
    )
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    issue_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="current")
    # Computed by services.py on create/update — stored for fast filtering
    risk_segment = models.CharField(
        max_length=10, choices=RISK_CHOICES, blank=True, default=""
    )

    class Meta:
        ordering = ["-issue_date"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["risk_segment"]),
            models.Index(fields=["purpose"]),
        ]

    def __str__(self):
        return (
            f"Loan #{self.id} | ${self.loan_amount} | "
            f"{self.status.upper()} | Risk: {self.risk_segment}"
        )
