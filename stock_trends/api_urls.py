"""stock_trends API URL configuration — DRF endpoints."""
from django.urls import path
from . import api_views

urlpatterns = [
    path("normalized-prices/", api_views.NormalizedPricesView.as_view(), name="normalized-prices"),
    path("volatility/", api_views.VolatilityView.as_view(), name="volatility"),
    path("moving-averages/", api_views.MovingAveragesView.as_view(), name="moving-averages"),
    path("correlation/", api_views.CorrelationView.as_view(), name="correlation"),
    path("risk-return/", api_views.RiskReturnView.as_view(), name="risk-return"),
    path("tickers/", api_views.TickerListView.as_view(), name="tickers"),
]
