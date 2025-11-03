# manage_staff_app/services.py
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # should be service_role for server operations
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TABLE = "front_desk_staff"

def list_staff(limit=100, offset=0):
    resp = supabase.table(TABLE).select("*").order("created_at", desc=False).limit(limit).offset(offset).execute()
    return resp

def get_staff_by_username(username):
    resp = supabase.table(TABLE).select("*").eq("username", username).execute()
    return resp

def create_staff(record: dict):
    # record should already contain hashed password
    resp = supabase.table(TABLE).insert(record).execute()
    return resp

def update_staff(username, updates: dict):
    resp = supabase.table(TABLE).update(updates).eq("username", username).execute()
    return resp

def deactivate_staff(username):
    resp = supabase.table(TABLE).update({"is_active": False}).eq("username", username).execute()
    return resp
