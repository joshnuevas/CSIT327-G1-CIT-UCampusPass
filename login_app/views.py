from django.shortcuts import render, redirect
from supabase import create_client
import os
from dotenv import load_dotenv
from django.contrib import messages
from django.contrib.auth.hashers import check_password

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def login_view(request):
    if request.method == 'POST':
        role = request.POST.get('role')
        identifier = request.POST.get('identifier').strip().lower()
        password = request.POST.get('password', '')

        # Define queries per role
        if role == 'visitor':
            user_resp = supabase.table("users").select("*").eq("email", identifier).execute()
            session_key = 'user_email'
            session_name = 'user_first_name'
            redirect_url = 'dashboard_app:dashboard'

        elif role == 'admin':
            user_resp = supabase.table("administrator").select("*").eq("username", identifier).execute()
            session_key = 'admin_username'
            session_name = 'admin_first_name'
            redirect_url = 'dashboard_app:admin_dashboard'

        elif role == 'staff':
            user_resp = supabase.table("front_desk_staff").select("*").eq("username", identifier).execute()
            session_key = 'staff_username'
            session_name = 'staff_first_name'
            redirect_url = 'dashboard_app:staff_dashboard'

        else:
            messages.error(request, "Invalid role selected.")
            return redirect('login_app:login')

        # Check if user exists
        if user_resp.data and len(user_resp.data) > 0:
            user = user_resp.data[0]
            stored_password = user.get('password', '')

            # Handle hashed and plain passwords
            if stored_password.startswith("pbkdf2_") or stored_password.startswith("argon2"):
                valid = check_password(password, stored_password)
            else:
                valid = password == stored_password

            if valid:
                request.session[session_key] = identifier
                request.session[session_name] = user.get('first_name')
                messages.success(request, "Login successful!")
                return redirect(redirect_url)
            else:
                messages.error(request, "Invalid credentials.")
        else:
            messages.error(request, "Invalid credentials.")

        return redirect('login_app:login')

    return render(request, 'login_app/login.html')


def logout_view(request):
    request.session.flush()
    return redirect('login_app:login')
