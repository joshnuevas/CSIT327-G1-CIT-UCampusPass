from django.urls import path
from .views import profile_view
from . import views

app_name = "profile_app"

urlpatterns = [
    path('', profile_view, name='profile'),
    path('admin/', views.admin_profile_view, name='admin_profile'),
    path("change-password/", views.change_password_request, name="change_password_request"),
]