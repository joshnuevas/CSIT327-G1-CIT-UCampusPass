# manage_admin_app/services.py
from supabase import create_client
from django.conf import settings

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def list_admins(limit: int = 500):
    return supabase.table("administrator").select("*").order("created_at", desc=False).limit(limit).execute()

def get_admin_by_username(username: str):
    return supabase.table("administrator").select("*").eq("username", username).execute()

def create_admin(data: dict):
    data.setdefault("is_active", True)
    data.setdefault("is_temp_password", True)
    # Create record (no .select("*") support here)
    resp = supabase.table("administrator").insert(data).execute()
    # Return inserted record by re-fetching it (optional, but keeps views consistent)
    if getattr(resp, "data", None):
        username = data.get("username")
        return get_admin_by_username(username)
    return resp

def update_admin(username: str, updates: dict):
    allowed_fields = ["first_name", "last_name", "email", "contact_number",
                      "password", "is_temp_password", "is_active"]
    clean_updates = {k: v for k, v in updates.items() if k in allowed_fields}
    resp = supabase.table("administrator").update(clean_updates).eq("username", username).execute()
    if getattr(resp, "status_code", None) == 200:
        return get_admin_by_username(username)
    return resp

def deactivate_admin(username: str):
    resp = supabase.table("administrator").update({"is_active": False}).eq("username", username).execute()
    if getattr(resp, "status_code", None) == 200:
        return get_admin_by_username(username)
    return resp

def activate_admin(username: str):
    resp = supabase.table("administrator").update({"is_active": True}).eq("username", username).execute()
    if getattr(resp, "status_code", None) == 200:
        return get_admin_by_username(username)
    return resp

def reset_admin_password(username: str, temp_password: str):
    from .helpers import hash_password
    hashed_pw = hash_password(temp_password)
    resp = supabase.table("administrator").update({
        "password": hashed_pw,
        "is_temp_password": True
    }).eq("username", username).execute()
    if getattr(resp, "status_code", None) == 200:
        return get_admin_by_username(username)
    return resp
