from supabase import create_client
from django.conf import settings
from datetime import datetime

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def list_logs(limit=1000):
    """
    Fetch logs from Supabase (latest first).
    """
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
    """
    Create a new system log entry.

    Parameters:
      actor (str): Who performed the action (e.g., "Juan Dela Cruz (admin123)")
      action_type (str): Type/category of action (e.g., "Account", "Visit", "Login")
      description (str): What was done
      actor_role (str): Role of the actor (e.g., "Admin", "Staff", "Visitor")
    """
    try:
        data = {
            "actor": actor,
            "action_type": action_type,
            "description": description,
            "actor_role": actor_role
        }
        supabase.table("system_logs").insert(data).execute()
    except Exception as e:
        print("Error creating log:", e)
