from django.shortcuts import render
from manage_staff_app.views import admin_required
from . import services
import json

@admin_required
def logs_view(request):
    logs = services.list_logs(limit=2000)
    return render(request, "manage_reports_logs_app/logs.html", {
        "logs_json": json.dumps(logs, default=str)
    })

@admin_required
def reports_view(request):
    """Main Reports page — summary + charts."""
    visits = services.list_visits(limit=2000)
    users = services.list_users(limit=2000)
    staff = services.list_staff(limit=1000)

    return render(request, "manage_reports_logs_app/reports.html", {
        "visits_json": json.dumps(visits, default=str),
        "users_json": json.dumps(users, default=str),
        "staff_json": json.dumps(staff, default=str)
    })
