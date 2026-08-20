"""
Stock Trends — Service Layer

Computes derived time-series metrics from raw OHLCV price history:
  - Daily returns (pct_change)
  - Rolling volatility (annualised)
  - Moving averages (MA20, MA50, MA200)
  - Correlation matrix between tickers
  - Normalized prices (base-100 indexed)
  - Risk-return summary

All computation done with pandas; no per-row derived columns stored in DB.
"""
import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
from django.db.models import Q

from .models import PriceHistory, Stock


# ─── Date Range Helpers ───────────────────────────────────────────────────────

_RANGE_DAYS = {
    "6M": 183,
    "1Y": 365,
    "3Y": 3 * 365,
    "ALL": None,
}


def _start_date(date_range: str) -> date | None:
    """Convert a range label ('6M', '1Y', '3Y', 'ALL') to a start date."""
    days = _RANGE_DAYS.get(date_range.upper(), 365)
    if days is None:
        return None
    return date.today() - timedelta(days=days)


def _price_df(tickers: list[str], date_range: str) -> pd.DataFrame:
    """
    Load OHLCV data for the given tickers and date range.
    Returns a DataFrame indexed by date with a MultiIndex on (ticker, date)
    or a simple pivot table with date as index and tickers as columns (close price).
    """
    start = _start_date(date_range)
    qs = PriceHistory.objects.filter(stock__ticker__in=tickers)
    if start:
        qs = qs.filter(date__gte=start)
    qs = qs.select_related("stock").values("stock__ticker", "date", "open", "high", "low", "close", "volume")

    df = pd.DataFrame(list(qs))
    if df.empty:
        return df

    df = df.rename(columns={"stock__ticker": "ticker"})
    df["date"] = pd.to_datetime(df["date"])
    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df


def _close_pivot(tickers: list[str], date_range: str) -> pd.DataFrame:
    """
    Return a pivot: index=date, columns=ticker, values=close price.
    Missing values forward-filled (handles weekends/holidays in synthetic data).
    """
    df = _price_df(tickers, date_range)
    if df.empty:
        return pd.DataFrame()
    pivot = df.pivot(index="date", columns="ticker", values="close").sort_index()
    pivot = pivot.ffill().dropna(how="all")
    return pivot


# ─── Analytics Functions ──────────────────────────────────────────────────────

def normalized_prices(tickers: list[str], date_range: str) -> dict:
    """
    Return close prices normalized to base-100 at the first available date.
    Enables fair visual comparison of stocks with very different price levels.

    Returns:
        {
          "dates": ["2024-01-02", ...],
          "series": [{"ticker": "AAPL", "data": [100.0, 102.3, ...]}, ...]
        }
    """
    pivot = _close_pivot(tickers, date_range)
    if pivot.empty:
        return {"dates": [], "series": []}

    # Normalize: divide every row by the first non-null value in each column × 100
    normed = pivot.div(pivot.iloc[0]) * 100

    dates = [d.strftime("%Y-%m-%d") for d in normed.index]
    series = [
        {"ticker": col, "data": [round(v, 2) if not math.isnan(v) else None for v in normed[col]]}
        for col in normed.columns
    ]
    return {"dates": dates, "series": series}


def rolling_volatility_series(tickers: list[str], date_range: str) -> dict:
    """
    Return 20-day rolling volatility (annualised) for each ticker.

    Volatility = std(daily_returns, window=20) × √252
    The √252 factor annualises the daily standard deviation.

    Returns:
        {
          "dates": [...],
          "series": [{"ticker": "AAPL", "data": [0.18, 0.22, ...]}, ...]
        }
    """
    pivot = _close_pivot(tickers, date_range)
    if pivot.empty:
        return {"dates": [], "series": []}

    returns = pivot.pct_change()
    vol = returns.rolling(window=20).std() * math.sqrt(252)  # annualise

    # Drop early rows where rolling window hasn't filled
    vol = vol.dropna(how="all")
    dates = [d.strftime("%Y-%m-%d") for d in vol.index]
    series = [
        {
            "ticker": col,
            "data": [round(v * 100, 2) if not math.isnan(v) else None for v in vol[col]],
        }
        for col in vol.columns
    ]
    return {"dates": dates, "series": series}


def moving_averages_series(tickers: list[str], date_range: str) -> dict:
    """
    Return close price + MA20 + MA50 + MA200 for each ticker.
    Used for the MA crossover chart — bullish signal when MA20 crosses above MA50.

    Returns:
        {
          "AAPL": {
            "dates": [...],
            "close": [...],
            "MA20": [...],
            "MA50": [...],
            "MA200": [...],
          },
          ...
        }
    """
    pivot = _close_pivot(tickers, date_range)
    if pivot.empty:
        return {}

    result = {}
    for ticker in pivot.columns:
        s = pivot[ticker].dropna()
        dates = [d.strftime("%Y-%m-%d") for d in s.index]
        result[ticker] = {
            "dates": dates,
            "close": [round(v, 2) for v in s.values],
            "MA20": [
                round(v, 2) if not math.isnan(v) else None
                for v in s.rolling(20).mean().values
            ],
            "MA50": [
                round(v, 2) if not math.isnan(v) else None
                for v in s.rolling(50).mean().values
            ],
            "MA200": [
                round(v, 2) if not math.isnan(v) else None
                for v in s.rolling(200).mean().values
            ],
        }
    return result


def correlation_matrix(tickers: list[str], date_range: str) -> dict:
    """
    Compute Pearson correlation matrix of daily returns across tickers.
    Correlation on *returns* (not prices) removes the trend component.

    Returns:
        {
          "labels": ["AAPL", "MSFT", ...],
          "matrix": [[1.0, 0.87, ...], ...]
        }
    """
    pivot = _close_pivot(tickers, date_range)
    if pivot.empty:
        return {"labels": [], "matrix": []}

    returns = pivot.pct_change().dropna(how="all")
    corr = returns.corr(method="pearson")

    labels = list(corr.columns)
    matrix = [
        [round(float(v), 3) if not math.isnan(v) else 0 for v in row]
        for row in corr.values
    ]
    return {"labels": labels, "matrix": matrix}


def risk_return_summary(date_range: str) -> list[dict]:
    """
    For every tracked stock compute annualised return vs annualised volatility.
    Used for the risk-return scatter plot (each ticker is a dot).

    Annualised return = (1 + cumulative_return)^(252/trading_days) - 1
    Annualised volatility = std(daily_returns) × √252
    """
    tickers = list(Stock.objects.values_list("ticker", flat=True))
    pivot = _close_pivot(tickers, date_range)
    if pivot.empty:
        return []

    returns = pivot.pct_change().dropna(how="all")
    result = []
    for ticker in pivot.columns:
        s = returns[ticker].dropna()
        if len(s) < 10:
            continue
        n = len(s)
        cumulative = (1 + s).prod() - 1
        ann_return = (1 + cumulative) ** (252 / n) - 1
        ann_vol = float(s.std()) * math.sqrt(252)
        result.append(
            {
                "ticker": ticker,
                "annualized_return": round(float(ann_return) * 100, 2),
                "annualized_volatility": round(ann_vol * 100, 2),
            }
        )
    return result
