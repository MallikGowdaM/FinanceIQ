"""stock_trends URL configuration — page views."""
from django.urls import path
from . import views

app_name = "stock_trends"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
]
