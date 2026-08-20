"""
Stock Trends — Django Admin registration.
"""
from django.contrib import admin
from .models import Stock, PriceHistory


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ["ticker", "name", "sector"]
    list_filter = ["sector"]
    search_fields = ["ticker", "name"]


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ["stock", "date", "open", "high", "low", "close", "volume"]
    list_filter = ["stock__ticker"]
    search_fields = ["stock__ticker"]
    ordering = ["-date"]
    date_hierarchy = "date"
