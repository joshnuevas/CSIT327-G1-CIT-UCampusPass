from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import StaffCreateForm, StaffEditForm
from .helpers import generate_staff_username, hash_password
from . import services
from manage_reports_logs_app import services as logs_services

# Import Notification Helper and Models
from dashboard_app.views import create_notification
from login_app.models import Administrator

# ===== Helper for Supabase Response Checking =====
def is_success(resp):
    """
    Checks if a Supabase response was successful.
    """
    if hasattr(resp, 'error') and resp.error:
        print(f"Supabase Error: {resp.error}") 
        return False
        
    data = getattr(resp, "data", None)
    if isinstance(data, dict) and 'code' in data and 'message' in data:
         print(f"Supabase Data Error: {data}")
         return False

    # Check strictly for data presence or success status codes if available
    if hasattr(resp, 'data') and resp.data:
        return True
    if hasattr(resp, 'status_code') and resp.status_code in (200, 201, 204):
        return True
        
    return False

# ===== NOTIFICATION HELPER =====
def send_staff_notifications(request, action_type, description):
    """
    Notify ALL other admins (and superadmins) about staff changes.
    
    Args:
        request: Request object (to identify the actor).
        action_type: "create", "update", "status_change", "security", "delete"
        description: The verb phrase (e.g., "has onboarded...").
    """
    try:
        current_admin_username = request.session.get('admin_username')
        actor_name = request.session.get('admin_first_name', current_admin_username)
        
        # Determine Title based on context
        title = "Staff Management"
        if action_type == "security":
            title = "Security Alert"
        elif action_type in ["create", "delete"]:
            title = "Staff Roster Update"
        elif action_type == "status_change":
            title = "Staff Status Update"

        # Fetch all admins to notify them
        all_admins = Administrator.objects.all()
        
        for admin in all_admins:
            # 1. Don't notify the one who performed the action
            if admin.username == current_admin_username:
                continue

            # 2. Notify everyone else
            create_notification(
                receiver_admin=admin,
                title=title,
                message=f"{actor_name} {description}",
                type="system_alert"
            )

    except Exception as e:
        print(f"Error sending staff notifications: {e}")


# ===== PERMISSION DECORATOR =====
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.session.get("admin_username") or request.session.get("user_is_superadmin"):
            return view_func(request, *args, **kwargs)
        messages.error(request, "You must be an admin to access this page.")
        return redirect("login_app:login")
    return wrapper


# ===== STAFF LIST =====
@admin_required
def staff_list_view(request):
    resp = services.list_staff(limit=500)
    staff = getattr(resp, "data", []) or []
    return render(request, "manage_staff_app/staff_list.html", {"staff_list": staff})


# ===== CREATE STAFF =====
@admin_required
def staff_create_view(request):
    if request.method == "POST":
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            existing_count = len(getattr(services.list_staff(limit=1000), "data", []) or [])
            username = generate_staff_username(data['first_name'], data['last_name'], existing_count)
            temp_pw = "123456" # Default temp password
            hashed = hash_password(temp_pw)

            record = {
                "username": username,
                "first_name": data['first_name'],
                "last_name": data['last_name'],
                "email": data.get('email'),
                "contact_number": data.get('contact_number'),
                "password": hashed,
                "is_temp_password": True,
                "is_active": True
            }

            resp = services.create_staff(record)

            if is_success(resp):
                # ✅ Log creation
                actor = f"{request.session.get('admin_first_name', 'Unknown')} ({request.session.get('admin_username', '-')})"
                logs_services.create_log(
                    actor,
                    "Staff Management",
                    f"Created new staff account '{username}'. Status: Success",
                    actor_role="Admin"
                )

                # 🔔 Notify other admins
                send_staff_notifications(
                    request,
                    "create",
                    f"has onboarded a new staff member: {data['first_name']} {data['last_name']} ({username})."
                )

                messages.success(request, f"Staff '{username}' created successfully.")
                return redirect("manage_staff_app:staff_list")
            else:
                messages.error(request, "Failed to create staff. Check logs.")
    else:
        form = StaffCreateForm()

    return render(request, "manage_staff_app/staff_form.html", {"form": form})


# ===== EDIT STAFF =====
@admin_required
def staff_edit_view(request, username):
    get_resp = services.get_staff_by_username(username)
    staff_data = getattr(get_resp, "data", [])
    if not staff_data:
        messages.error(request, f"Staff '{username}' not found.")
        return redirect("manage_staff_app:staff_list")

    staff = staff_data[0]
    if request.method == "POST":
        form = StaffEditForm(request.POST)
        if form.is_valid():
            updates = form.cleaned_data
            # Preserve the current is_active state
            updates["is_active"] = staff.get("is_active", True)
            resp = services.update_staff(username, updates)
            
            if is_success(resp):
                # ✅ Log edit
                actor = f"{request.session.get('admin_first_name', 'Unknown')} ({request.session.get('admin_username', '-')})"
                logs_services.create_log(
                    actor,
                    "Staff Management",
                    f"Edited staff details for '{username}'. Status: Success",
                    actor_role="Admin"
                )

                # 🔔 Notify other admins
                send_staff_notifications(
                    request,
                    "update",
                    f"has updated the profile details for staff member {username}."
                )

                messages.success(request, f"Staff '{username}' updated successfully.")
                return redirect("manage_staff_app:staff_list")
            else:
                messages.error(request, f"Failed to update staff '{username}'.")
    else:
        initial = {
            "first_name": staff.get("first_name"),
            "last_name": staff.get("last_name"),
            "email": staff.get("email"),
            "contact_number": staff.get("contact_number")
        }
        form = StaffEditForm(initial=initial)

    return render(request, "manage_staff_app/staff_form.html", {"form": form, "editing": True, "username": username})


# ===== ACTIVATE/DEACTIVATE STAFF =====
@admin_required
def staff_deactivate_view(request, username):
    get_resp = services.get_staff_by_username(username)
    staff_data = getattr(get_resp, "data", [])
    if not staff_data:
        messages.error(request, "Staff not found.")
        return redirect("manage_staff_app:staff_list")

    staff = staff_data[0]
    current_status = staff.get("is_active", True)
    new_status = not current_status
    
    # Professional phrasing
    action_desc = "activated the account for" if new_status else "deactivated the account for"
    simple_action = "activated" if new_status else "deactivated"

    resp = services.update_staff(username, {"is_active": new_status})

    if is_success(resp):
        # ✅ Log activation/deactivation
        actor = f"{request.session.get('admin_first_name', 'Unknown')} ({request.session.get('admin_username', '-')})"
        logs_services.create_log(
            actor,
            "Staff Management",
            f"{simple_action.capitalize()} staff account '{username}'. Status: Success",
            actor_role="Admin"
        )

        # 🔔 Notify other admins
        send_staff_notifications(
            request,
            "status_change",
            f"has {action_desc} staff member {username}."
        )

        messages.success(request, f"Staff '{username}' has been {simple_action}.")
    else:
        messages.error(request, f"Failed to update status for '{username}'.")

    return redirect("manage_staff_app:staff_list")


# ===== RESET PASSWORD =====
@admin_required
def staff_reset_password_view(request, username):
    temp_pw = "123456"
    hashed = hash_password(temp_pw)
    resp = services.update_staff(username, {"password": hashed, "is_temp_password": True})
    
    if is_success(resp):
        # ✅ Log reset
        actor = f"{request.session.get('admin_first_name', 'Unknown')} ({request.session.get('admin_username', '-')})"
        logs_services.create_log(
            actor,
            "Security",
            f"Reset password for staff '{username}'. Status: Success",
            actor_role="Admin"
        )

        # 🔔 Notify other admins (Security Alert)
        send_staff_notifications(
            request,
            "security",
            f"has triggered a security password reset for staff member {username}."
        )

        messages.success(request, f"Password reset for '{username}'. Temporary password: {temp_pw}.")
    else:
        messages.error(request, f"Failed to reset password for '{username}'.")

    return redirect("manage_staff_app:staff_list")


@admin_required
def staff_delete_view(request, username):
    get_resp = services.get_staff_by_username(username)
    staff_data = getattr(get_resp, "data", [])
    if not staff_data:
        messages.error(request, "Staff not found.")
        return redirect("manage_staff_app:staff_list")

    # Safety check: Prevent admin from deleting themselves via this view (unlikely, but good practice)
    if username == request.session.get('admin_username'):
        messages.error(request, "You cannot delete your own account.")
        return redirect("manage_staff_app:staff_list")

    resp = services.delete_staff(username)

    if is_success(resp):
        # ✅ Log deletion
        actor = f"{request.session.get('admin_first_name', 'Unknown')} ({request.session.get('admin_username', '-')})"
        logs_services.create_log(
            actor,
            "Staff Management",
            f"Deleted staff account '{username}'. Status: Success",
            actor_role="Admin"
        )

        # 🔔 Notify other admins
        send_staff_notifications(
            request,
            "delete",
            f"has permanently deleted the staff account for {username}."
        )

        messages.success(request, f"Staff '{username}' has been deleted.")
    else:
        messages.error(request, f"Failed to delete staff '{username}'.")

    return redirect("manage_staff_app:staff_list")