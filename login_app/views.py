from django.shortcuts import render, redirect
from supabase import create_client
import os
from dotenv import load_dotenv
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.messages import get_messages

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def login_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip().lower()
        password = request.POST.get('password', '')
        valid = False

        # Auto-detect role based on identifier
        if '@' in identifier:
            # Assume visitor (email)
            role = 'visitor'
            user_resp = supabase.table("users").select("*").eq("email", identifier).execute()
            session_key = 'user_email'
            session_name = 'user_first_name'
            redirect_url = 'dashboard_app:dashboard'
        else:
            # Assume username, try admin first
            user_resp = supabase.table("administrator").select("*").eq("username", identifier).execute()
            if user_resp.data and len(user_resp.data) > 0:
                role = 'admin'
                session_key = 'admin_username'
                session_name = 'admin_first_name'
                redirect_url = 'dashboard_app:admin_dashboard'
            else:
                # Try staff
                user_resp = supabase.table("front_desk_staff").select("*").eq("username", identifier).execute()
                if user_resp.data and len(user_resp.data) > 0:
                    role = 'staff'
                    session_key = 'staff_username'
                    session_name = 'staff_first_name'
                    redirect_url = 'dashboard_app:staff_dashboard'
                else:
                    messages.error(request, "Invalid credentials.")
                    return redirect('login_app:login')

        # Check if user exists
        if user_resp.data and len(user_resp.data) > 0:
            user = user_resp.data[0]
            stored_password = user.get('password', '')

            # Password verification
            if stored_password.startswith("pbkdf2_") or stored_password.startswith("argon2"):
                valid = check_password(password, stored_password)
            else:
                valid = password == stored_password

            if valid:
                # Check if staff or admin account is active
                if role in ['staff', 'admin'] and not user.get('is_active', True):
                    messages.error(request, "Your account has been deactivated.")
                    return redirect('login_app:login')

                # Store main session
                request.session[session_key] = identifier
                request.session[session_name] = user.get('first_name')

                # Mark superadmin if admin
                if role == 'admin':
                    request.session['user_is_superadmin'] = user.get('is_superadmin', False)

                # Check for temporary password (force change)
                if user.get("is_temp_password", False) and role in ['admin', 'staff']:
                    request.session["force_pw_role"] = role
                    request.session["force_pw_user"] = identifier
                    messages.warning(request, "Please change your temporary password.")
                    return redirect("login_app:change_temp_password")

                return redirect(redirect_url)
            else:
                messages.error(request, "Invalid credentials.")
        else:
            messages.error(request, "Invalid credentials.")

        return redirect('login_app:login')

    return render(request, 'login_app/login.html')



def change_temp_password_view(request):
    """
    Page to force admins or staff with temporary passwords to create a new one.
    """
    username = request.session.get("force_pw_user")
    role = request.session.get("force_pw_role")

    if not username or not role:
        messages.error(request, "Session expired. Please log in again.")
        return redirect("login_app:login")

    # Determine the Supabase table based on role
    table = "front_desk_staff" if role == "staff" else "administrator"

    if request.method == "POST":
        new_pw = request.POST.get("new_password")
        confirm_pw = request.POST.get("confirm_password")

        if new_pw != confirm_pw:
            messages.error(request, "Passwords do not match.")
            return redirect("login_app:change_temp_password")

        hashed_pw = make_password(new_pw)

        # Update the record in Supabase
        resp = supabase.table(table).update({
            "password": hashed_pw,
            "is_temp_password": False
        }).eq("username", username).execute()

        if getattr(resp, "data", None):
            messages.success(request, "Password changed successfully! Please log in again.")
            # Clear temp password session keys
            request.session.pop("force_pw_user", None)
            request.session.pop("force_pw_role", None)
            return redirect("login_app:login")
        else:
            messages.error(request, "Failed to update password. Please try again.")
            return redirect("login_app:change_temp_password")

    return render(request, "login_app/change_temp_password.html")


def logout_view(request):
    # Completely clear session and messages
    storage = get_messages(request)
    for _ in storage:
        pass  # iterate to clear existing messages

    request.session.flush()
    return redirect('login_app:login')
