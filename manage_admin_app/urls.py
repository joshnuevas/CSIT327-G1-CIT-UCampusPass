# manage_admin_app/urls.py
from django.urls import path
from . import views

app_name = "manage_admin_app"

urlpatterns = [
    path("", views.admin_list_view, name="admin_list"),
    path("create/", views.admin_create_view, name="admin_create"),
    path("edit/<str:username>/", views.admin_edit_view, name="admin_edit"),
    path("toggle-active/<str:username>/", views.admin_toggle_active_view, name="admin_toggle_active"),
    path("reset-password/<str:username>/", views.admin_reset_password_view, name="admin_reset_password"),
]
    