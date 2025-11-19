# staff_visit_records_app/services.py
from dashboard_app.models import Visit
from datetime import datetime, date, timedelta
import pytz

def get_all_visits(limit=2000):
    """
    Fetch all visit records using Django ORM, ordered from latest to oldest.
    """
    try:
        visits = Visit.objects.all().order_by('-visit_date', '-start_time')[:limit]
        # Convert to list of dictionaries for compatibility
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
            'user_id': visit.user_id
        } for visit in visits]
    except Exception as e:
        print(f"Error fetching visits: {e}")
        return []

def categorize_visits(visits):
    """
    Categorize visits into the five groups.
    """
    manila_tz = pytz.timezone('Asia/Manila')
    today = datetime.now(manila_tz).date()

    all_visits = visits
    upcoming_visits = []
    today_upcoming_visits = []
    active_visits = []
    checked_out_visits = []

    for visit in visits:
        status = visit.get('status', '').lower()
        visit_date = visit.get('visit_date')
        start_time = visit.get('start_time')
        end_time = visit.get('end_time')

        # Categorize based on status and timing
        if status == 'upcoming':
            upcoming_visits.append(visit)
            if visit_date == today:
                today_upcoming_visits.append(visit)

        elif status == 'active' or status == 'ongoing':
            active_visits.append(visit)

        elif status == 'completed' or status == 'expired':
            # ✅ Use visit_date instead of end_time.date()
            if visit_date and (visit_date == today or visit_date >= today - timedelta(days=7)):
                checked_out_visits.append(visit)

    return {
        'all_visits': all_visits,
        'upcoming_visits': upcoming_visits,
        'today_upcoming_visits': today_upcoming_visits,
        'active_visits': active_visits,
        'checked_out_visits': checked_out_visits,
    }
