"""
Root URL configuration for the Finance Analytics Dashboard.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("loan-risk/", include("loan_risk.urls")),
    path("stock-trends/", include("stock_trends.urls")),
    path("spending/", include("spending.urls")),
    # API namespace — each app registers its own DRF routes
    path("api/loan-risk/", include("loan_risk.api_urls")),
    path("api/stock-trends/", include("stock_trends.api_urls")),
    path("api/spending/", include("spending.api_urls")),
]
