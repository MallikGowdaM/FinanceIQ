"""spending URL configuration — page views."""
from django.urls import path
from . import views

app_name = "spending"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
]
