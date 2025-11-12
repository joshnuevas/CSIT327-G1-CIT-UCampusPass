from django.urls import path
from .views import history_view, cancel_visit

app_name = "history_app"

urlpatterns = [
    path('', history_view, name='visit_history'),
    path('cancel/', cancel_visit, name='cancel_visit'),
]