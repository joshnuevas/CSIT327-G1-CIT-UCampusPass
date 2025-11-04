# manage_admin_app/helpers.py
import re
from django.contrib.auth.hashers import make_password
import random
import string

def generate_admin_username(first_name: str, last_name: str, existing_count: int = None) -> str:
    """
    Generate a unique admin username.
    Format: cit_admin01, cit_admin02, etc.
    Optionally uses existing_count to avoid collisions.
    """
    base = "cit_admin"
    suffix = f"{(existing_count or 0) + 1:02d}"
    return f"{base}{suffix}"


def generate_temp_password() -> str:
    """
    Always return a fixed temporary password for new or reset admins.
    """
    return "123456"



def hash_password(plain: str) -> str:
    """
    Hash a plain-text password using Django's make_password.
    """
    return make_password(plain)
