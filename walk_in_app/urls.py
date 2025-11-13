"""
Walk-In Registration App URLs
"""

from django.urls import path
from . import views

app_name = 'walk_in_app'

urlpatterns = [
    path('registration/', views.walk_in_registration, name='registration'),
]