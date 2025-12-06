# profile_app/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
import re
from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError
from manage_reports_logs_app import services as logs_services
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.views.decorators.http import require_http_methods
from profile_app.tokens import simple_token_generator
from login_app.models import PasswordResetToken


from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Import Django models
from register_app.models import User
from login_app.models import Administrator

# ---------------- Profile View ----------------
def profile_view(request):
    if 'user_email' not in request.session:
        return redirect('login_app:login')
    
    user_email = request.session['user_email']

    # Load current user
    try:
        user = User.objects.get(email=user_email)
    except User.DoesNotExist:
        messages.error(request, "User not found. Please log in again.")
        return redirect('login_app:login')

    if request.method == 'POST':
        action = request.POST.get('action')

        # --------------- Update Personal Info ---------------
        if action == 'update_info':
            first_name = (request.POST.get('first_name') or '').strip()
            last_name = (request.POST.get('last_name') or '').strip()
            email = (request.POST.get('email') or '').strip().lower()
            phone = (request.POST.get('phone') or '').strip()

            # Handle visitor type - either from dropdown or "Other" input
            visitor_type_dropdown = request.POST.get('visitorType')
            if visitor_type_dropdown == 'Other':
                visitor_type = (request.POST.get('visitor_type_other') or '').strip()
                if not visitor_type:
                    messages.error(request, "Please specify your visitor type.")
                    return redirect('profile_app:profile')
            else:
                visitor_type = visitor_type_dropdown

            # Basic required checks
            if not first_name or not last_name or not email or not phone:
                messages.error(request, "Please complete all required fields.")
                return redirect('profile_app:profile')

            # ✅ Validate phone format: must be 11 digits starting with 09
            if not re.fullmatch(r"09\d{9}$", phone):
                messages.error(request, "Invalid phone number format. It should be 11 digits and start with 09.")
                return redirect('profile_app:profile')

            # ✅ Validate email format (e.g., name@example.com)
            email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$"
            if not re.fullmatch(email_pattern, email):
                messages.error(request, "Please enter a valid email address (e.g., name@example.com).")
                return redirect('profile_app:profile')

            # Check if email or phone already used by another account
            if User.objects.filter(email=email).exclude(email=user_email).exists():
                messages.error(request, "Email already registered.")
                return redirect('profile_app:profile')

            if User.objects.filter(phone=phone).exclude(email=user_email).exists():
                messages.error(request, "Phone already registered.")
                return redirect('profile_app:profile')

            # Update user
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.phone = phone
            user.visitor_type = visitor_type
            user.save()

            # Update session values so header and profile stay in sync
            request.session['user_email'] = email
            request.session['user_first_name'] = first_name
            request.session['user_last_name'] = last_name

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
            
            user.delete()
            request.session.flush()
            messages.success(request, "Account deleted permanently.")
            return redirect('login_app:login')

    # GET → render profile page
    return render(request, 'profile_app/profile.html', {
        "user": user,
        "user_first_name": request.session.get("user_first_name"),
        "user_last_name": request.session.get("user_last_name"),
    })

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

def change_password_request(request):
    # Session-based authentication for visitor users
    if "user_email" not in request.session:
        return redirect("login_app:login")

    user = User.objects.get(email=request.session["user_email"])

    if request.method == "POST":
        # Create password reset token
        reset_token = PasswordResetToken.objects.create(user=user)

        reset_url = request.build_absolute_uri(
            reverse("login_app:reset_password", args=[reset_token.token])
        )

        subject = "Campus Pass - Change Password"
        body_text = (
            f"Hi {user.first_name},\n\n"
            "You requested to change your Campus Pass password.\n"
            f"Click the link below to set a new password:\n\n{reset_url}\n\n"
            "If you did not request this, you may ignore this email.\n\n"
            "CIT-U Campus Pass"
        )

        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            message = Mail(
                from_email=settings.DEFAULT_FROM_EMAIL,
                to_emails=user.email,
                subject=subject,
                plain_text_content=body_text,
            )
            sg.send(message)
            messages.success(request, "A password change link has been sent to your email.")
        except Exception:
            messages.error(request, "Unable to send email right now. Please try again later.")

        return redirect("profile_app:change_password_request")

    # GET → Show the page
    return render(request, "profile_app/change_password_request.html", {"user": user})
