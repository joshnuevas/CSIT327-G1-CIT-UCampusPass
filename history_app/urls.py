from django.urls import path
from .views import history_view

app_name = "history_app"

urlpatterns = [
    path('', history_view, name='visit_history'),
]
