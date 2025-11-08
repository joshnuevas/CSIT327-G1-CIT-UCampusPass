# manage_reports_logs_app/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from manage_staff_app.views import admin_required
from . import services
import json

@admin_required
def logs_view(request):
    logs = services.list_logs(limit=2000)
    # print("Fetched logs:", logs)

    return render(request, "manage_reports_logs_app/logs.html", {
        "logs_json": json.dumps(logs, default=str)  # For JS use
    })
