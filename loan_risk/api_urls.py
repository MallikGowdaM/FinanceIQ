"""loan_risk API URL configuration — DRF endpoints."""
from django.urls import path
from . import api_views

app_name = "api_loan_risk"

urlpatterns = [
    path("default-by-credit-band/", api_views.DefaultByCreditBandView.as_view(), name="default-by-credit-band"),
    path("default-by-dti/", api_views.DefaultByDTIView.as_view(), name="default-by-dti"),
    path("risk-distribution/", api_views.RiskDistributionView.as_view(), name="risk-distribution"),
    path("scatter/", api_views.IncomeVsLoanScatterView.as_view(), name="scatter"),
    path("risk-drivers/", api_views.RiskDriversView.as_view(), name="risk-drivers"),
    path("predict/", api_views.PredictRiskView.as_view(), name="predict"),
    path("summary/", api_views.SummaryKPIsView.as_view(), name="summary"),
]

