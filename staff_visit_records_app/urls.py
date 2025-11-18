from django.urls import path
from . import views

app_name = 'staff_visit_records_app'

urlpatterns = [
    path('', views.staff_visit_records_view, name='staff_visit_records'),
    path('check-in/', views.check_in_visitor, name='check_in_visitor'),
    path('check-out/', views.check_out_visitor, name='check_out_visitor'),
]