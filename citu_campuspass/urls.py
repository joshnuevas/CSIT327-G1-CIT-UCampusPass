"""
URL configuration for citu_campuspass project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard_app.urls', namespace="dashboard_app")),
    path('register/', include('register_app.urls', namespace="register_app")),
    path('login/', include('login_app.urls', namespace="login_app")),
    path('book-visit/', include('book_visit_app.urls', namespace="book_visit_app")),
    path('history/', include('history_app.urls', namespace="history_app")),
    path('profile/', include('profile_app.urls', namespace="profile_app")),
    path('help/', include('help_app.urls', namespace="help_app")),
    path("manage-staff/", include("manage_staff_app.urls", namespace="manage_staff_app")),
    path("manage-visitors/", include("manage_visitor_app.urls", namespace="manage_visitor_app")),
    path("manage-admins/", include("manage_admin_app.urls", namespace="manage_admin_app")),
]