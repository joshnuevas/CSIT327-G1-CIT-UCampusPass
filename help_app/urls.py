from django.urls import path
from . import views

app_name = "help_app"

urlpatterns = [
    path('', views.help_support_view, name='help_support'),
]