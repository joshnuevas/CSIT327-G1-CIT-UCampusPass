# login_app/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.contrib.messages import get_messages
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


from .models import Administrator, FrontDeskStaff, PasswordResetToken
from register_app.models import User  # Visitor User model

import re


def is_strong_password(password):
    """
    Same rules as your register_app.register_view:
    - At least 8 characters
    - At least one uppercase
    - At least one lowercase
    - At least one number
    - At least one special character
    """
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True


def login_view(request):
    if request.method == 'POST':
        # Handle change password form
        if 'change_password' in request.POST:
            new_pw = request.POST.get("new_password")
            confirm_pw = request.POST.get("confirm_password")
            temp_username = request.POST.get("temp_username")
            temp_role = request.POST.get("temp_role")

            if new_pw != confirm_pw:
                messages.error(request, "Passwords do not match.")
                return render(request, 'login_app/login.html', {
                    'show_change_password': True,
                    'temp_username': temp_username,
                    'temp_role': temp_role
                })

            if not is_strong_password(new_pw):
                messages.error(request, "Password too weak. Must contain uppercase, lowercase, number, and special character.")
                return render(request, 'login_app/login.html', {
                    'show_change_password': True,
                    'temp_username': temp_username,
                    'temp_role': temp_role
                })

            try:
                # Update using Django ORM
                if temp_role == "staff":
                    user = FrontDeskStaff.objects.get(username=temp_username)
                else:  # admin
                    user = Administrator.objects.get(username=temp_username)

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
                return render(request, 'login_app/login.html')
            except Exception:
                messages.error(request, "Failed to update password. Please try again.")
                return render(request, 'login_app/login.html', {
                    'show_change_password': True,
                    'temp_username': temp_username,
                    'temp_role': temp_role
                })

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

                # 🔹 Store last name per role
                if role == 'visitor':
                    request.session['user_last_name'] = getattr(user_obj, 'last_name', "") or ""
                elif role == 'staff':
                    request.session['staff_last_name'] = getattr(user_obj, 'last_name', "") or ""
                elif role == 'admin':
                    request.session['admin_last_name'] = getattr(user_obj, 'last_name', "") or ""

                # Mark superadmin if admin
                if role == 'admin':
                    request.session['user_is_superadmin'] = getattr(user_obj, 'is_superadmin', False)

                # Check for temporary password (force change)
                if getattr(user_obj, "is_temp_password", False) and role in ['admin', 'staff']:
                    request.session["force_pw_role"] = role
                    request.session["force_pw_user"] = identifier
                    messages.warning(request, "Please change your temporary password.")
                    # Render login page with change password form instead of redirecting
                    return render(request, 'login_app/login.html', {
                        'show_change_password': True,
                        'temp_username': identifier,
                        'temp_role': role
                    })

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
        except Exception:
            messages.error(request, "Failed to update password. Please try again.")
            return redirect("login_app:change_temp_password")

    return render(request, "login_app/change_temp_password.html")


def forgot_password_view(request):
    """
    Forgot password for VISITOR users (email-based login).
    Uses SendGrid Web API to send the reset link.
    """
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if not email:
            messages.error(request, "Please enter your email address.")
            return redirect("login_app:forgot_password")

        # Try to find user – but don't reveal if it exists (security)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.success(
                request,
                "If that email is registered, a password reset link has been sent."
            )
            return redirect("login_app:login")

        # Create token
        reset_token = PasswordResetToken.objects.create(user=user)

        reset_url = request.build_absolute_uri(
            reverse("login_app:reset_password", args=[reset_token.token])
        )

        subject = "Campus Pass - Password Reset"
        body_text = (
            f"Hi {user.first_name},\n\n"
            "You requested a password reset for your Campus Pass account.\n"
            f"Click the link below to set a new password:\n\n{reset_url}\n\n"
            "If you did not request this, you can ignore this email.\n\n"
            "CIT-U Campus Pass"
        )

        # --- SendGrid Web API send ---
        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            message = Mail(
                from_email=settings.DEFAULT_FROM_EMAIL,
                to_emails=user.email,
                subject=subject,
                plain_text_content=body_text,
            )
            response = sg.send(message)

            # SendGrid returns 202 for accepted
            if response.status_code in (200, 202):
                messages.success(
                    request,
                    "If that email is registered, a password reset link has been sent."
                )
            else:
                messages.error(
                    request,
                    "We couldn't send the reset email right now. Please try again later."
                )

        except Exception as e:
            # Optional: log this if you want
            print("Error sending SendGrid email:", e)
            messages.error(
                request,
                "There was a problem sending the reset email. Please try again later."
            )

        return redirect("login_app:login")

    # GET
    return render(request, "login_app/forgot_password.html")

def reset_password_view(request, token):
    """
    Reset password view for visitors, using the emailed token.
    """
    reset_token = get_object_or_404(PasswordResetToken, token=token)

    # Check if token expired
    if reset_token.is_expired():
        reset_token.delete()
        messages.error(request, "This reset link has expired. Please request a new one.")
        return redirect("login_app:forgot_password")

    if request.method == "POST":
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("login_app:reset_password", token=token)

        if not is_strong_password(password):
            messages.error(
                request,
                "Password too weak. Must contain uppercase, lowercase, number, "
                "and special character."
            )
            return redirect("login_app:reset_password", token=token)

        user = reset_token.user
        user.set_password(password)
        user.save()

        # One-time use
        reset_token.delete()

        messages.success(request, "Your password has been updated. You can now sign in.")
        return redirect("login_app:login")

    # GET
    return render(request, "login_app/reset_password.html", {"token": token})


def logout_view(request):
    # Completely clear session and messages
    storage = get_messages(request)
    for _ in storage:
        pass  # iterate to clear existing messages

    request.session.flush()
    return redirect('login_app:login')
