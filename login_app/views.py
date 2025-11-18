# login_app/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.contrib.messages import get_messages
from .models import Administrator, FrontDeskStaff
from register_app.models import User  # Import your User model

def login_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip().lower()
        password = request.POST.get('password', '')
        valid = False
        user_obj = None
        role = None

        # Auto-detect role based on identifier
        if '@' in identifier:
            # Assume visitor (email) - Use Django ORM
            role = 'visitor'
            try:
                user_obj = User.objects.get(email=identifier)
                session_key = 'user_email'
                session_name = 'user_first_name'
                redirect_url = 'dashboard_app:dashboard'
            except User.DoesNotExist:
                user_obj = None
        else:
            # Assume username, try admin first - Use Django ORM
            try:
                user_obj = Administrator.objects.get(username=identifier)
                role = 'admin'
                session_key = 'admin_username'
                session_name = 'admin_first_name'
                redirect_url = 'dashboard_app:admin_dashboard'
            except Administrator.DoesNotExist:
                # Try staff - Use Django ORM
                try:
                    user_obj = FrontDeskStaff.objects.get(username=identifier)
                    role = 'staff'
                    session_key = 'staff_username'
                    session_name = 'staff_first_name'
                    redirect_url = 'dashboard_app:staff_dashboard'
                except FrontDeskStaff.DoesNotExist:
                    user_obj = None

        # Check if user exists and validate password
        if user_obj:
            # Password verification using model methods
            if hasattr(user_obj, 'check_password'):
                valid = user_obj.check_password(password)
            else:
                # Fallback for plain text passwords (if any)
                stored_password = user_obj.password
                if stored_password.startswith("pbkdf2_") or stored_password.startswith("argon2"):
                    valid = check_password(password, stored_password)
                else:
                    valid = password == stored_password

            if valid:
                # Check if staff or admin account is active
                if role in ['staff', 'admin'] and not getattr(user_obj, 'is_active', True):
                    messages.error(request, "Your account has been deactivated.")
                    return redirect('login_app:login')

                # Store main session
                request.session[session_key] = identifier
                request.session[session_name] = user_obj.first_name

                # Mark superadmin if admin
                if role == 'admin':
                    request.session['user_is_superadmin'] = getattr(user_obj, 'is_superadmin', False)

                # Check for temporary password (force change)
                if getattr(user_obj, "is_temp_password", False) and role in ['admin', 'staff']:
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

    if request.method == "POST":
        new_pw = request.POST.get("new_password")
        confirm_pw = request.POST.get("confirm_password")

        if new_pw != confirm_pw:
            messages.error(request, "Passwords do not match.")
            return redirect("login_app:change_temp_password")

        try:
            # Update using Django ORM
            if role == "staff":
                user = FrontDeskStaff.objects.get(username=username)
            else:  # admin
                user = Administrator.objects.get(username=username)
            
            user.set_password(new_pw)
            user.is_temp_password = False
            user.save()

            messages.success(request, "Password changed successfully! Please log in again.")
            # Clear temp password session keys
            request.session.pop("force_pw_user", None)
            request.session.pop("force_pw_role", None)
            return redirect("login_app:login")
            
        except (FrontDeskStaff.DoesNotExist, Administrator.DoesNotExist):
            messages.error(request, "User not found. Please log in again.")
            return redirect("login_app:login")
        except Exception as e:
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