"""loan_risk URL configuration — page views."""
from django.urls import path
from . import views

app_name = "loan_risk"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
]
