# manage_staff_app/urls.py
from django.urls import path
from . import views

app_name = "manage_staff_app"

urlpatterns = [
    path("", views.staff_list_view, name="staff_list"),
    path("create/", views.staff_create_view, name="staff_create"),
    path("edit/<str:username>/", views.staff_edit_view, name="staff_edit"),
    path("deactivate/<str:username>/", views.staff_deactivate_view, name="staff_deactivate"),
    path("reset-password/<str:username>/", views.staff_reset_password_view, name="staff_reset_password"),
]
