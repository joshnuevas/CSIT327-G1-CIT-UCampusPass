from django.urls import path
from . import views

urlpatterns = [
    path('', views.help_support_view, name='help_support'),
]