# manage_visit_records_app/services.py
from supabase import create_client
from django.conf import settings

# Initialize Supabase
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def list_visits(limit=1000):
    """
    Fetch all visit records from Supabase.
    """
    visits_resp = (
        supabase.table("visits")
        .select("*")
        .order("visit_id")  # ascending by default
        .limit(limit)
        .execute()
    )
    return visits_resp.data  # ✅ Return only the data list
