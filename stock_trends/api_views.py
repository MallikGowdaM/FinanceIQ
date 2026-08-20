"""
Stock Trends — DRF API Views.
Each view calls services.py for analytics and returns clean JSON.
"""
from rest_framework.views import APIView
from rest_framework.response import Response

from . import services
from .models import Stock


class TickerListView(APIView):
    """GET /api/stock-trends/tickers/
    Returns all available tickers with name + sector.
    """
    def get(self, request):
        stocks = list(Stock.objects.values("ticker", "name", "sector"))
        return Response(stocks)


class NormalizedPricesView(APIView):
    """GET /api/stock-trends/normalized-prices/?tickers=AAPL,MSFT&range=1Y
    Returns base-100 normalized close prices per day.
    """
    def get(self, request):
        tickers = request.query_params.get("tickers", "AAPL,MSFT,GOOGL")
        ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
        date_range = request.query_params.get("range", "1Y")
        data = services.normalized_prices(ticker_list, date_range)
        return Response(data)


class VolatilityView(APIView):
    """GET /api/stock-trends/volatility/?tickers=AAPL,MSFT&range=1Y
    Returns rolling 20-day annualised volatility per ticker.
    """
    def get(self, request):
        tickers = request.query_params.get("tickers", "AAPL,MSFT,GOOGL")
        ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
        date_range = request.query_params.get("range", "1Y")
        data = services.rolling_volatility_series(ticker_list, date_range)
        return Response(data)


class MovingAveragesView(APIView):
    """GET /api/stock-trends/moving-averages/?tickers=AAPL&range=1Y
    Returns close + MA20 + MA50 + MA200 per ticker per day.
    """
    def get(self, request):
        tickers = request.query_params.get("tickers", "AAPL")
        ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
        date_range = request.query_params.get("range", "1Y")
        data = services.moving_averages_series(ticker_list, date_range)
        return Response(data)


class CorrelationView(APIView):
    """GET /api/stock-trends/correlation/?tickers=AAPL,MSFT,GOOGL&range=1Y
    Returns correlation matrix of daily returns.
    """
    def get(self, request):
        tickers = request.query_params.get("tickers", "AAPL,MSFT,GOOGL,AMZN,META")
        ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
        date_range = request.query_params.get("range", "1Y")
        data = services.correlation_matrix(ticker_list, date_range)
        return Response(data)


class RiskReturnView(APIView):
    """GET /api/stock-trends/risk-return/?range=1Y
    Returns annualised return vs volatility per ticker for scatter plot.
    """
    def get(self, request):
        date_range = request.query_params.get("range", "1Y")
        data = services.risk_return_summary(date_range)
        return Response(data)
