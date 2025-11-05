from django.urls import path
from . import views

app_name = "visit_records_app"

urlpatterns = [
    path("", views.visit_records_view, name="visit_records"),
]
