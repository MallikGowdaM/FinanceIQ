"""spending API URL configuration — DRF endpoints."""
from django.urls import path
from . import api_views

urlpatterns = [
    path("category-breakdown/", api_views.CategoryBreakdownView.as_view(), name="category-breakdown"),
    path("budget-vs-actual/", api_views.BudgetVsActualView.as_view(), name="budget-vs-actual"),
    path("income-expense-trend/", api_views.IncomeExpenseTrendView.as_view(), name="income-expense-trend"),
    path("kpis/", api_views.SpendingKPIsView.as_view(), name="kpis"),
    path("transactions/", api_views.TransactionCreateView.as_view(), name="transactions"),
    path("spending-leaks/", api_views.SpendingLeaksView.as_view(), name="spending-leaks"),
    path("available-months/", api_views.AvailableMonthsView.as_view(), name="available-months"),
]
