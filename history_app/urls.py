from django.urls import path
from .views import history_view

urlpatterns = [
    path('history/', history_view, name='visit_history'),
]
