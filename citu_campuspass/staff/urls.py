from django.urls import path
from . import views

app_name = 'staff'

urlpatterns = [
    path('register/', views.register, name='staff_register'),
    path('login/', views.login, name='staff_login'),
]
