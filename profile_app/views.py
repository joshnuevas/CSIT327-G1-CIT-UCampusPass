from django.shortcuts import render, redirect
from supabase import create_client
from django.contrib import messages
from dotenv import load_dotenv
import os
import re
from django.contrib.auth.hashers import check_password, make_password
from manage_reports_logs_app import services as logs_services

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- Profile View ----------------
def profile_view(request):
    if 'user_email' not in request.session:
        return redirect('login_app:login')
    
    user_email = request.session['user_email']
    user_resp = supabase.table("users").select("*").eq("email", user_email).execute()
    user = user_resp.data[0] if user_resp.data else {}

    if request.method == 'POST':
        action = request.POST.get('action')

        # --------------- Update Personal Info ---------------
        if action == 'update_info':
            first_name = request.POST.get('first_name').strip()
            last_name = request.POST.get('last_name').strip()
            email = request.POST.get('email').strip().lower()
            phone = request.POST.get('phone').strip()
            
            # Handle visitor type - either from dropdown or "Other" input
            visitor_type_dropdown = request.POST.get('visitorType')
            if visitor_type_dropdown == 'Other':
                visitor_type = request.POST.get('visitor_type_other', '').strip()
                if not visitor_type:
                    messages.error(request, "Please specify your visitor type.")
                    return redirect('profile_app:profile')
            else:
                visitor_type = visitor_type_dropdown

            # Validate phone format
            if not re.fullmatch(r"09\d{9}$", phone):
                messages.error(request, "Invalid phone number format.")
                return redirect('profile_app:profile')

            # Check if email or phone exists (other than current user)
            email_exist = supabase.table("users").select("*").ilike("email", email).neq("email", user_email).execute()
            phone_exist = supabase.table("users").select("*").eq("phone", phone).neq("email", user_email).execute()
            if email_exist.data:
                messages.error(request, "Email already registered.")
                return redirect('profile_app:profile')
            if phone_exist.data:
                messages.error(request, "Phone already registered.")
                return redirect('profile_app:profile')

            supabase.table("users").update({
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "visitor_type": visitor_type
            }).eq("email", user_email).execute()

            # Update session email if changed
            request.session['user_email'] = email
            request.session['user_first_name'] = first_name
            messages.success(request, "Profile updated successfully!")
            return redirect('profile_app:profile')

        # --------------- Change Password ---------------
        elif action == 'change_password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if not check_password(current_password, user['password']):
                messages.error(request, "Current password is incorrect.")
                return redirect('profile_app:profile')

            if new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
                return redirect('profile_app:profile')

            hashed_password = make_password(new_password)
            supabase.table("users").update({"password": hashed_password}).eq("email", user_email).execute()
            messages.success(request, "Password changed successfully!")
            return redirect('profile_app:profile')

        # --------------- Delete Account ---------------
        elif action == 'delete_account':
            password = request.POST.get('delete_password')
            if not check_password(password, user['password']):
                messages.error(request, "Password incorrect. Cannot delete account.")
                return redirect('profile_app:profile')
            
            supabase.table("users").delete().eq("email", user_email).execute()
            request.session.flush()
            messages.success(request, "Account deleted permanently.")
            return redirect('login_app:login')

    return render(request, 'profile_app/profile.html', {"user": user})

def admin_profile_view(request):
    if 'admin_username' not in request.session:
        return redirect('login_app:login')

    username = request.session['admin_username']
    response = supabase.table("administrator").select("*").eq("username", username).execute()
    admin_data = response.data[0] if response.data else {}

    if request.method == "POST":
        action = request.POST.get("action")

        # ----- Update Personal Info -----
        if action == "update_info":
            first_name = request.POST["first_name"]
            last_name = request.POST["last_name"]
            email = request.POST["email"]

            # Capture old values for logging
            old_first = admin_data.get("first_name", "")
            old_last = admin_data.get("last_name", "")
            old_email = admin_data.get("email", "")

            # Update Supabase
            supabase.table("administrator").update({
                "first_name": first_name,
                "last_name": last_name,
                "email": email
            }).eq("username", username).execute()

            # Update session for header initials
            request.session["admin_first_name"] = first_name

            # Log profile update
            actor = f"{request.session.get('admin_first_name', 'Unknown')} ({username})"
            description = (
                f"Updated profile: first_name '{old_first}' → '{first_name}', "
                f"last_name '{old_last}' → '{last_name}', "
                f"email '{old_email}' → '{email}'"
            )
            logs_services.create_log(actor, "Account", description, actor_role="Admin")

            messages.success(request, "Profile updated successfully!")
            return redirect("profile_app:admin_profile")

        # ----- Change Password -----
        elif action == "change_password":
            current_password = request.POST.get("current_password")
            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")

            if not check_password(current_password, admin_data.get('password', '')):
                messages.error(request, "Current password is incorrect.")
                return redirect("profile_app:admin_profile")

            if new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
                return redirect("profile_app:admin_profile")

            hashed_password = make_password(new_password)
            supabase.table("administrator").update({"password": hashed_password}).eq("username", username).execute()

            # Log password change
            actor = f"{request.session.get('admin_first_name', 'Unknown')} ({username})"
            logs_services.create_log(actor, "Security", "Changed password", actor_role="Admin")

            messages.success(request, "Password changed successfully!")
            return redirect("profile_app:admin_profile")

    context = {"admin": admin_data}
    return render(request, "profile_app/admin_profile.html", context)