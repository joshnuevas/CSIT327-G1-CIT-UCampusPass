from django.urls import path
from . import views

app_name = "book_visit_app"

urlpatterns = [
    path('', views.book_visit_view, name='book_visit'),
]
