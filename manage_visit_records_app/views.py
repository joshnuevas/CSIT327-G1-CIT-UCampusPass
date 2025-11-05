# manage_visit_records_app/views.py
import json
from django.shortcuts import render
from manage_staff_app.views import admin_required
from . import services

@admin_required
def visit_records_view(request):
    visits = services.list_visits(limit=2000) or []

    # Convert to JSON for the JS script tag
    visits_json = json.dumps(visits, default=str)

    return render(request, "manage_visit_records_app/visit_records.html", {
        "visits": visits_json,
    })
