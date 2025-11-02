# manage_staff_app/helpers.py
import re
from django.contrib.auth.hashers import make_password
import random
import string

def generate_staff_username(first_name: str, last_name: str, existing_count: int = None) -> str:
    # e.g., cit_staff01, cit_staff02
    # You can query Supabase to decide the number; existing_count optional usage.
    base = "cit_staff"
    # If you want more uniqueness: use initials + number
    # safe numeric suffix
    suffix = f"{(existing_count or 0) + 1:02d}"
    return f"{base}{suffix}"

def generate_temp_password() -> str:
    return "123456"


def hash_password(plain: str) -> str:
    return make_password(plain)
