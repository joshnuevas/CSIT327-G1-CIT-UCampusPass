# manage_visit_records_app/views.py
import json
from django.shortcuts import render
from django.http import JsonResponse
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

@admin_required
def export_visits_view(request):
    """AJAX endpoint for exporting visit records with filters"""
    # Get filter parameters
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', 'All')
    register_date = request.GET.get('register_date', '')

    # Get all visits (no limit for export)
    visits = services.list_visits(limit=None) or []

    # Apply filters
    filtered_visits = []
    for visit in visits:
        # Search filter
        if search:
            query = search.lower()
            text = f"{visit.get('user_email', '')} {visit.get('code', '')} {visit.get('purpose', '')} {visit.get('department', '')} {visit.get('visitor_name', '')}".lower()
            if query not in text:
                continue

        # Status filter
        if status != 'All' and visit.get('status', '').lower() != status.lower():
            continue

        # Date filter
        if register_date:
            visit_date = str(visit.get('visit_date', '')).split('T')[0]  # Get YYYY-MM-DD
            if visit_date != register_date:
                continue

        filtered_visits.append(visit)

    return JsonResponse({
        'visits': filtered_visits,
        'total_count': len(filtered_visits)
    })
