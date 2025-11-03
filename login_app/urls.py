from django.urls import path
from . import views
app_name = "login_app"
urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),  
]
