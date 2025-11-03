from django.urls import path
from . import views

app_name = "manage_visitor_app"

urlpatterns = [
    path("", views.visitor_list_view, name="visitor_list"),
    path("delete/<int:user_id>/", views.visitor_deactivate_view, name="visitor_deactivate"),
]
