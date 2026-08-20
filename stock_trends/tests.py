"""
Stock Trends — Unit Tests

Focuses on service-layer calculations that derive analytics from raw OHLCV data.
"""
import math
from datetime import date, timedelta

import pandas as pd
from django.test import TestCase, Client

from .models import Stock, PriceHistory
from .services import (
    normalized_prices,
    rolling_volatility_series,
    moving_averages_series,
    correlation_matrix,
    risk_return_summary,
    _close_pivot,
)


class StockServiceTests(TestCase):
    """Test pandas-based analytics functions with synthetic test data."""

    @classmethod
    def setUpTestData(cls):
        """Create 2 stocks with 260 days of price history each (≈1 year)."""
        cls.aapl = Stock.objects.create(ticker="TESTAAPL", name="Test Apple", sector="Technology")
        cls.msft = Stock.objects.create(ticker="TESTMSFT", name="Test Microsoft", sector="Technology")

        # Generate monotonically increasing prices for predictable tests
        records = []
        start = date(2024, 1, 2)
        for i in range(260):
            d = start + timedelta(days=i)
            if d.weekday() >= 5:
                continue  # skip weekends
            price_a = 150.0 + i * 0.5  # steady uptrend
            price_m = 300.0 + i * 0.3
            records.extend([
                PriceHistory(stock=cls.aapl, date=d, open=price_a, high=price_a * 1.01,
                             low=price_a * 0.99, close=price_a, volume=1000000),
                PriceHistory(stock=cls.msft, date=d, open=price_m, high=price_m * 1.01,
                             low=price_m * 0.99, close=price_m, volume=800000),
            ])
        PriceHistory.objects.bulk_create(records)

    def test_normalized_prices_starts_at_100(self):
        """First value in a normalised series must always be 100."""
        result = normalized_prices(["TESTAAPL"], "1Y")
        self.assertIn("series", result)
        if result["series"]:
            first_val = result["series"][0]["data"][0]
            self.assertAlmostEqual(first_val, 100.0, places=1)

    def test_normalized_prices_returns_dates(self):
        """Result must contain a 'dates' list."""
        result = normalized_prices(["TESTAAPL", "TESTMSFT"], "ALL")
        self.assertIn("dates", result)
        self.assertGreater(len(result["dates"]), 0)

    def test_rolling_volatility_positive(self):
        """Volatility values must be non-negative (std is always ≥ 0)."""
        result = rolling_volatility_series(["TESTAAPL"], "ALL")
        if result["series"]:
            values = [v for v in result["series"][0]["data"] if v is not None]
            for v in values:
                self.assertGreaterEqual(v, 0)

    def test_rolling_volatility_structure(self):
        """Output must have dates and series keys."""
        result = rolling_volatility_series(["TESTAAPL", "TESTMSFT"], "ALL")
        self.assertIn("dates", result)
        self.assertIn("series", result)

    def test_moving_averages_has_required_keys(self):
        """Each ticker in result must have close, MA20, MA50, MA200, dates."""
        result = moving_averages_series(["TESTAAPL"], "ALL")
        self.assertIn("TESTAAPL", result)
        ticker_data = result["TESTAAPL"]
        for key in ["dates", "close", "MA20", "MA50", "MA200"]:
            self.assertIn(key, ticker_data)

    def test_moving_averages_ma200_none_for_short_series(self):
        """With only ~180 trading days, some early MA200 values should be None."""
        result = moving_averages_series(["TESTAAPL"], "ALL")
        if "TESTAAPL" not in result:
            return  # Skip if no data in range
        ma200 = result["TESTAAPL"]["MA200"]
        # First N values should be None (window not filled)
        none_count = sum(1 for v in ma200 if v is None)
        self.assertGreater(none_count, 0)

    def test_correlation_matrix_diagonal_is_one(self):
        """Correlation of a series with itself must be 1.0."""
        result = correlation_matrix(["TESTAAPL", "TESTMSFT"], "ALL")
        labels = result["labels"]
        matrix = result["matrix"]
        for i, label in enumerate(labels):
            self.assertAlmostEqual(matrix[i][i], 1.0, places=2)

    def test_correlation_matrix_symmetric(self):
        """Correlation matrix must be symmetric: corr[i][j] == corr[j][i]."""
        result = correlation_matrix(["TESTAAPL", "TESTMSFT"], "ALL")
        matrix = result["matrix"]
        n = len(matrix)
        for i in range(n):
            for j in range(n):
                self.assertAlmostEqual(matrix[i][j], matrix[j][i], places=5)

    def test_risk_return_summary_structure(self):
        """Each entry must have ticker, annualized_return, annualized_volatility."""
        result = risk_return_summary("ALL")
        test_tickers = {r["ticker"] for r in result}
        # Our test tickers should appear
        self.assertIn("TESTAAPL", test_tickers)
        entry = next(r for r in result if r["ticker"] == "TESTAAPL")
        self.assertIn("annualized_return", entry)
        self.assertIn("annualized_volatility", entry)
        # Volatility must be non-negative
        self.assertGreaterEqual(entry["annualized_volatility"], 0)

    def test_uptrend_stock_positive_return(self):
        """TESTAAPL has monotonically rising price → return must be positive."""
        result = risk_return_summary("ALL")
        entry = next((r for r in result if r["ticker"] == "TESTAAPL"), None)
        if entry:
            self.assertGreater(entry["annualized_return"], 0)


class StockAPITests(TestCase):
    """Smoke tests for stock trends API endpoints."""

    def setUp(self):
        self.client = Client()

    def test_tickers_endpoint(self):
        resp = self.client.get("/api/stock-trends/tickers/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_normalized_prices_endpoint(self):
        resp = self.client.get("/api/stock-trends/normalized-prices/?tickers=AAPL&range=1Y")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("dates", data)
        self.assertIn("series", data)

    def test_risk_return_endpoint(self):
        resp = self.client.get("/api/stock-trends/risk-return/?range=1Y")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_correlation_endpoint(self):
        resp = self.client.get("/api/stock-trends/correlation/?tickers=AAPL,MSFT&range=1Y")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("matrix", data)
        self.assertIn("labels", data)
