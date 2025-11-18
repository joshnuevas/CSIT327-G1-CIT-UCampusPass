# staff_visit_records_app/services.py
from supabase import create_client
from django.conf import settings
from datetime import datetime, date, timedelta
import pytz

# Initialize Supabase
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def get_all_visits(limit=2000):
    """
    Fetch all visit records from Supabase, ordered from latest to oldest.
    """
    visits_resp = (
        supabase.table("visits")
        .select("*")
        .order("visit_date", desc=True)
        .order("start_time", desc=True)
        .limit(limit)
        .execute()
    )
    return visits_resp.data

def categorize_visits(visits):
    """
    Categorize visits into the five groups.
    """
    now = datetime.now(pytz.UTC)
    manila_tz = pytz.timezone('Asia/Manila')
    today = datetime.now(manila_tz).date()

    all_visits = visits
    upcoming_visits = []
    today_upcoming_visits = []
    active_visits = []
    checked_out_visits = []

    for visit in visits:
        status = visit.get('status', '').lower()
        visit_date_str = visit.get('visit_date')
        start_time_str = visit.get('start_time')
        end_time_str = visit.get('end_time')

        # Parse visit date
        visit_date = None
        if visit_date_str:
            try:
                visit_date = datetime.strptime(visit_date_str[:10], '%Y-%m-%d').date()
            except:
                visit_date = None


        # Parse times if available
        start_time = None
        end_time = None
        if start_time_str and visit_date:
            try:
                # Combine date and time
                start_datetime_str = f"{visit_date_str} {start_time_str}"
                start_time = datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M:%S')
                start_time = pytz.UTC.localize(start_time)
            except:
                start_time = None
        if end_time_str and visit_date:
            try:
                end_datetime_str = f"{visit_date_str} {end_time_str}"
                end_time = datetime.strptime(end_datetime_str, '%Y-%m-%d %H:%M:%S')
                end_time = pytz.UTC.localize(end_time)
            except:
                end_time = None

        # Categorize based on status and timing
        if status == 'upcoming':
            upcoming_visits.append(visit)
            if visit_date == today:
                today_upcoming_visits.append(visit)
        elif status == 'active' or status == 'ongoing':
            active_visits.append(visit)
        elif status == 'completed' or status == 'expired':
            # Include completed visits from today or recent (last 7 days)
            if end_time and (end_time.date() == today or end_time > now - timedelta(days=7)):
                checked_out_visits.append(visit)

    return {
        'all_visits': all_visits,
        'upcoming_visits': upcoming_visits,
        'today_upcoming_visits': today_upcoming_visits,
        'active_visits': active_visits,
        'checked_out_visits': checked_out_visits,
    }