# manage_reports_logs_app/urls.py
from django.urls import path
from . import views

app_name = "manage_reports_logs_app"

urlpatterns = [
    path("logs/", views.logs_view, name="logs_view"),
]
