from supabase import create_client
from django.conf import settings
from datetime import datetime

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# ==============================
# LOGS SERVICES
# ==============================
def list_logs(limit=1000):
    """Fetch all system logs."""
    try:
        response = (
            supabase.table("system_logs")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as e:
        print("Error fetching logs:", e)
        return []

def create_log(actor, action_type, description, actor_role=""):
    """Create a new system log entry."""
    try:
        data = {
            "actor": actor,
            "action_type": action_type,
            "description": description,
            "actor_role": actor_role,
        }
        supabase.table("system_logs").insert(data).execute()
    except Exception as e:
        print("Error creating log:", e)

# ==============================
# REPORTS SERVICES
# ==============================
def list_visits(limit=2000):
    """Fetch visit data."""
    try:
        resp = (
            supabase.table("visits")
            .select("visit_id, user_id, purpose, department, status, created_at, visit_date")
            .order("visit_date", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        print("Error fetching visits:", e)
        return []

def list_users(limit=2000):
    """Fetch visitor data."""
    try:
        resp = (
            supabase.table("users")
            .select("user_id, first_name, last_name, visitor_type, created_at")
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        print("Error fetching users:", e)
        return []

def list_staff(limit=1000):
    """Fetch staff data for charts and filters."""
    try:
        resp = (
            supabase.table("front_desk_staff")
            .select("staff_id, first_name, last_name, created_at, is_active")
            .order("first_name", desc=False)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        print("Error fetching staff:", e)
        return []
