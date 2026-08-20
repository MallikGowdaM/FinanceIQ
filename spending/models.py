"""
Spending — Data Models

Category: an expense/income category with a monthly budget limit.
Transaction: a single financial transaction.
"""
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    budget_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monthly budget cap for this category (0 = no limit / income)",
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.name} (budget: ${self.budget_limit}/mo)"


class Transaction(models.Model):
    TYPE_CHOICES = [
        ("income", "Income"),
        ("expense", "Expense"),
    ]
    PAYMENT_METHOD_CHOICES = [
        ("cash", "Cash"),
        ("credit_card", "Credit Card"),
        ("debit_card", "Debit Card"),
        ("bank_transfer", "Bank Transfer"),
        ("upi", "UPI / Digital Wallet"),
        ("other", "Other"),
    ]

    date = models.DateField(db_index=True)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Always positive; type determines direction"
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="transactions"
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, default="credit_card"
    )

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["type"]),
            models.Index(fields=["category", "date"]),
        ]

    def __str__(self):
        sign = "+" if self.type == "income" else "-"
        return f"{self.date} | {self.description} | {sign}${self.amount}"
