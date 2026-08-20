"""
Stock Trends — Data Models

Stock: a financial instrument (ticker, name, sector).
PriceHistory: daily OHLCV price record for a stock.
"""
from django.db import models


class Stock(models.Model):
    SECTOR_CHOICES = [
        ("Technology", "Technology"),
        ("Healthcare", "Healthcare"),
        ("Financials", "Financials"),
        ("Energy", "Energy"),
        ("Consumer Discretionary", "Consumer Discretionary"),
        ("Consumer Staples", "Consumer Staples"),
        ("Industrials", "Industrials"),
        ("Utilities", "Utilities"),
        ("Real Estate", "Real Estate"),
        ("Materials", "Materials"),
        ("Communication Services", "Communication Services"),
    ]

    ticker = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    sector = models.CharField(max_length=40, choices=SECTOR_CHOICES)

    class Meta:
        ordering = ["ticker"]

    def __str__(self):
        return f"{self.ticker} — {self.name}"


class PriceHistory(models.Model):
    stock = models.ForeignKey(
        Stock, on_delete=models.CASCADE, related_name="price_history"
    )
    date = models.DateField(db_index=True)
    open = models.DecimalField(max_digits=12, decimal_places=4)
    high = models.DecimalField(max_digits=12, decimal_places=4)
    low = models.DecimalField(max_digits=12, decimal_places=4)
    close = models.DecimalField(max_digits=12, decimal_places=4)
    volume = models.BigIntegerField()

    class Meta:
        # Compound index on (stock, date) — most queries filter by both
        unique_together = [["stock", "date"]]
        ordering = ["stock", "date"]
        indexes = [
            models.Index(fields=["stock", "date"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self):
        return f"{self.stock.ticker} | {self.date} | Close: {self.close}"
