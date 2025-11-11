from django.urls import path
from . import views

app_name = "dashboard_app"

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('admin_dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('staff_dashboard/', views.staff_dashboard_view, name='staff_dashboard'),
    path('api/admin-notifications/', views.admin_notifications_api, name='admin_notifications_api'),
    path('api/admin-notifications/delete/', views.delete_notification_api, name='delete_notification_api'),
    path('api/admin-notifications/clear/', views.clear_notifications_api, name='clear_notifications_api'),
]

