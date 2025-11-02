from django.urls import path
from . import views

app_name = "dashboard_app"

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('admin_dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('staff_dashboard/', views.staff_dashboard_view, name='staff_dashboard'),
]
