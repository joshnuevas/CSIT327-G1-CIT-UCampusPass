# manage_visit_records_app/services.py
from dashboard_app.models import Visit

def list_visits(limit=1000):
    """
    Fetch all visit records using Django ORM.
    """
    try:
        queryset = Visit.objects.all().order_by('visit_id')
        if limit is not None:
            queryset = queryset[:limit]
        visits = queryset
        # Convert to list of dictionaries for JSON serialization
        return [{
            'visit_id': visit.visit_id,
            'user_email': visit.user_email,
            'code': visit.code,
            'purpose': visit.purpose,
            'department': visit.department,
            'visit_date': visit.visit_date,
            'start_time': visit.start_time,
            'end_time': visit.end_time,
            'status': visit.status,
            'created_at': visit.created_at,
            'user_id': visit.user_id,
            'visitor_name': visit.visitor_name if hasattr(visit, 'visitor_name') else None
        } for visit in visits]
    except Exception as e:
        print(f"Error fetching visits: {e}")
        return []