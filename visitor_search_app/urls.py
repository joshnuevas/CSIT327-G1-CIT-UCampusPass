"""
Visitor Search App URLs
"""

from django.urls import path
from . import views

app_name = 'visitor_search_app'

urlpatterns = [
    path('search/', views.visitor_search, name='search'),
    path('detail/', views.visitor_detail, name='detail'),
]