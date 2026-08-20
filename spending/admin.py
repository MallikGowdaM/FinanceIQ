"""
Spending — Django Admin registration.
"""
from django.contrib import admin
from .models import Category, Transaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "budget_limit"]
    search_fields = ["name"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["date", "description", "amount", "type", "category", "payment_method"]
    list_filter = ["type", "category", "payment_method"]
    search_fields = ["description"]
    ordering = ["-date"]
    date_hierarchy = "date"
