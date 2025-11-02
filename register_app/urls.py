from django.urls import path
from . import views

app_name = "register_app"

urlpatterns = [
    path('', views.register_view, name='register'),
]
