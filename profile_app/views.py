# profile_app/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
import re
from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError
from manage_reports_logs_app import services as logs_services

# Import Django models
from register_app.models import User
from login_app.models import Administrator

# ---------------- Profile View ----------------
def profile_view(request):
    if 'user_email' not in request.session:
        return redirect('login_app:login')
    
    user_email = request.session['user_email']
    
    # Use Django ORM instead of Supabase
    try:
        user = User.objects.get(email=user_email)
    except User.DoesNotExist:
        messages.error(request, "User not found. Please log in again.")
        return redirect('login_app:login')

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
            if User.objects.filter(email=email).exclude(email=user_email).exists():
                messages.error(request, "Email already registered.")
                return redirect('profile_app:profile')
            if User.objects.filter(phone=phone).exclude(email=user_email).exists():
                messages.error(request, "Phone already registered.")
                return redirect('profile_app:profile')

            # Update user using Django ORM
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.phone = phone
            user.visitor_type = visitor_type
            user.save()

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

            if not user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
                return redirect('profile_app:profile')

            if new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
                return redirect('profile_app:profile')

            # Update password using model method
            user.set_password(new_password)
            user.save()
            
            messages.success(request, "Password changed successfully!")
            return redirect('profile_app:profile')

        # --------------- Delete Account ---------------
        elif action == 'delete_account':
            password = request.POST.get('delete_password')
            if not user.check_password(password):
                messages.error(request, "Password incorrect. Cannot delete account.")
                return redirect('profile_app:profile')
            
            # Delete user using Django ORM
            user.delete()
            request.session.flush()
            messages.success(request, "Account deleted permanently.")
            return redirect('login_app:login')

    return render(request, 'profile_app/profile.html', {"user": user})

def admin_profile_view(request):
    if 'admin_username' not in request.session:
        return redirect('login_app:login')

    username = request.session['admin_username']
    
    # Use Django ORM instead of Supabase
    try:
        admin = Administrator.objects.get(username=username)
    except Administrator.DoesNotExist:
        messages.error(request, "Admin not found. Please log in again.")
        return redirect('login_app:login')

    if request.method == "POST":
        action = request.POST.get("action")

        # ----- Update Personal Info -----
        if action == "update_info":
            first_name = request.POST["first_name"]
            last_name = request.POST["last_name"]
            email = request.POST["email"]

            # Capture old values for logging
            old_first = admin.first_name
            old_last = admin.last_name
            old_email = getattr(admin, 'email', '')

            # Update using Django ORM
            admin.first_name = first_name
            admin.last_name = last_name
            admin.email = email
            admin.save()

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

            if not admin.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
                return redirect("profile_app:admin_profile")

            if new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
                return redirect("profile_app:admin_profile")

            # Update password using model method
            admin.set_password(new_password)
            admin.save()

            # Log password change
            actor = f"{request.session.get('admin_first_name', 'Unknown')} ({username})"
            logs_services.create_log(actor, "Security", "Changed password", actor_role="Admin")

            messages.success(request, "Password changed successfully!")
            return redirect("profile_app:admin_profile")

    context = {"admin": admin}
    return render(request, "profile_app/admin_profile.html", context)