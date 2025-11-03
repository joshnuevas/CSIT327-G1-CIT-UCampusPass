from supabase import create_client
from django.conf import settings

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def list_visitors(limit=500):
    """
    Fetch only visitors from the 'users' table.
    We assume visitor_type is set for visitors (e.g., 'guest', 'parent', 'student', etc.)
    """
    return (
        supabase.table("users")
        .select("*")
        .neq("visitor_type", None)
        .order("user_id", desc=False) 
        .limit(limit)
        .execute()
    )


def deactivate_visitor(user_id):
    """Deactivate visitor by removing or marking them inactive (if you have a status column)"""
    # If you plan to add an is_active column later, you can update that here.
    # For now, this just deletes the record or could be changed to an update.
    return supabase.table("users").delete().eq("user_id", user_id).execute()


def get_visitor_by_id(user_id):
    """Fetch a single visitor by user_id"""
    return supabase.table("users").select("*").eq("user_id", user_id).execute()
