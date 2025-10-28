from django.urls import path
from . import views

app_name = 'staff'

urlpatterns = [
    path('register/', views.register, name='staff_register'),
]
