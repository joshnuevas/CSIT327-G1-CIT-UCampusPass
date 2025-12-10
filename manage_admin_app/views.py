from django.shortcuts import render, redirect
from django.contrib import messages
from . import services
from .forms import AdminCreateForm, AdminEditForm
from .helpers import hash_password, generate_admin_username, generate_temp_password
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

    return True

# ===== NOTIFICATION HELPER =====
def send_admin_notifications(request, action_type, target_username, description):
    """
    Handles routing notifications to the correct admins/superadmins.
    
    Args:
        request: The request object.
        action_type: "create", "update", "status_change", "security", "delete"
        target_username: The username of the admin being affected.
        description: A verb phrase describing the action (e.g., "updated the profile for...").
    """
    try:
        current_admin_username = request.session.get('admin_username')
        actor_name = request.session.get('admin_first_name', current_admin_username)
        
        all_admins = Administrator.objects.all()
        target_admin = next((a for a in all_admins if a.username == target_username), None)
        
        # Format the base message: "John Doe [description]"
        # Example: "John Doe has reset the password for admin123."
        system_message = f"{actor_name} {description}"

        for admin in all_admins:
            # 1. Skip the actor (don't notify yourself)
            if admin.username == current_admin_username:
                continue

            # 2. Logic for SUPERADMINS (They get a system overview)
            if admin.is_superadmin:
                create_notification(
                    receiver_admin=admin,
                    title=f"Admin Management: {action_type.replace('_', ' ').title()}",
                    message=system_message,
                    type="system_alert"
                )
                continue

            # 3. Logic for REGULAR ADMINS
            # Rule A: The specific admin being modified gets a personal alert
            if admin.username == target_username:
                if action_type in ["update", "security", "status_change"]:
                    create_notification(
                        receiver_admin=admin,
                        title="Account Security Update",
                        message=f"Administrative action by {actor_name}: {description}",
                        type="personal_alert"
                    )
            
            # Rule B: Other admins get team updates (only for major events like create/delete)
            else:
                if action_type in ["create", "delete", "status_change"]:
                    create_notification(
                        receiver_admin=admin,
                        title="Team Roster Update",
                        message=system_message,
                        type="system_alert"
                    )

    except Exception as e:
        print(f"Error sending notifications: {e}")

# ===== PERMISSION DECORATOR =====
def superadmin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.session.get("user_is_superadmin"):
            return view_func(request, *args, **kwargs)
        messages.error(request, "You must be a superadmin to access this page.")
        return redirect("login_app:login")
    return wrapper


# ===== VIEWS =====

@superadmin_required
def admin_list_view(request):
    """Display the list of administrators."""
    resp = services.list_admins(limit=500)
    admins = getattr(resp, "data", []) or []
    return render(request, "manage_admin_app/admin_list.html", {
        "admin_list": admins, 
        "logged_in_username": request.session.get('admin_username')
    })


@superadmin_required
def admin_create_view(request):
    """Create a new administrator."""
    if request.method == "POST":
        form = AdminCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            # Generate unique username
            resp_list = services.list_admins(limit=500)
            existing_count = len(getattr(resp_list, "data", []) or [])
            username = generate_admin_username(data['first_name'], data['last_name'], existing_count)

            # Generate temporary password
            temp_pw = generate_temp_password()
            hashed_pw = hash_password(temp_pw)

            # Prepare record
            record = {
                **data,
                "username": username,
                "password": hashed_pw,
                "is_temp_password": True,
                "is_active": True,
                "is_superadmin": False 
            }

            # Create admin
            resp = services.create_admin(record)
            success = is_success(resp)

            # Logging
            actor = f"{request.session.get('admin_first_name', 'Unknown')} ({request.session.get('admin_username', '-')})"
            logs_services.create_log(
                actor,
                "Account",
                f"Created new admin account '{username}'. Status: {'Success' if success else 'Failed'}",
                actor_role="Admin"
            )

            if success:
                # NOTIFICATION: New Admin Created
                send_admin_notifications(
                    request, 
                    "create", 
                    username, 
                    f"has onboarded a new administrator: {data['first_name']} {data['last_name']} ({username})."
                )

                messages.success(request, f"Admin '{username}' created with temporary password '{temp_pw}'.")
                return redirect("manage_admin_app:admin_list")
            else:
                messages.error(request, f"Failed to create admin. Supabase response: {resp}")
                return redirect("manage_admin_app:admin_create")
        else:
            messages.error(request, f"Invalid form data: {form.errors}")
            return redirect("manage_admin_app:admin_create")
    else:
        form = AdminCreateForm()

    return render(request, "manage_admin_app/admin_form.html", {"form": form})


@superadmin_required
def admin_edit_view(request, username):
    """Edit an existing administrator."""
    get_resp = services.get_admin_by_username(username)
    admin_data = getattr(get_resp, "data", [])
    
    if not admin_data:
        messages.error(request, "Admin not found.")
        return redirect("manage_admin_app:admin_list")
    
    admin = admin_data[0]

    if request.method == "POST":
        form = AdminEditForm(request.POST)
        if form.is_valid():
            updates = form.cleaned_data

            if 'is_active' not in request.POST:
                raw_val = admin.get('is_active')
                if raw_val is None:
                    current_active = True
                elif isinstance(raw_val, bool):
                    current_active = raw_val
                else:
                    current_active = str(raw_val).lower() in ('true', '1', 't')
                updates['is_active'] = current_active

            resp = services.update_admin(username, updates)
            success = is_success(resp)

            # Logging
            actor = f"{request.session.get('admin_first_name', 'Unknown')} ({request.session.get('admin_username', '-')})"
            logs_services.create_log(
                actor,
                "Account",
                f"Edited admin details for '{username}'. Status: {'Success' if success else 'Failed'}",
                actor_role="Admin"
            )

            if success:
                # NOTIFICATION: Admin Details Updated
                send_admin_notifications(
                    request, 
                    "update", 
                    username, 
                    f"has updated profile details for administrator {username}."
                )

                messages.success(request, f"Admin '{username}' updated successfully.")
            else:
                messages.error(request, f"Failed to update admin. Check database permissions.")

            return redirect("manage_admin_app:admin_list")
        else:
            messages.error(request, f"Invalid form data: {form.errors}")
    else:
        form = AdminEditForm(initial=admin)

    return render(request, "manage_admin_app/admin_form.html", {
        "form": form,
        "editing": True,
        "username": username
    })


@superadmin_required
def admin_toggle_superadmin_view(request, username):
    """Toggles the is_superadmin status."""
    get_resp = services.get_admin_by_username(username)
    admin_data = getattr(get_resp, "data", [])
    
    if not admin_data:
        messages.error(request, "Admin not found.")
        return redirect("manage_admin_app:admin_list")

    admin = admin_data[0]
    
    raw_status = admin.get("is_superadmin")
    if isinstance(raw_status, bool):
        current_status = raw_status
    else:
        current_status = str(raw_status).lower() in ('true', '1', 't')

    new_status = not current_status
    # Professional phrasing for the message
    action_desc = "granted superadmin privileges to" if new_status else "revoked superadmin privileges from"
    
    resp = services.update_admin(username, {"is_superadmin": new_status})
    
    if is_success(resp):
        # Verify step
        verify_resp = services.get_admin_by_username(username)
        verify_data = getattr(verify_resp, "data", [])
        
        if verify_data:
            db_val = verify_data[0].get("is_superadmin")
            db_bool = db_val if isinstance(db_val, bool) else str(db_val).lower() in ('true', '1', 't')
            
            if db_bool == new_status:
                actor = f"{request.session.get('admin_first_name', 'Unknown')} ({request.session.get('admin_username', '-')})"
                logs_services.create_log(
                    actor,
                    "Account",
                    f"{action_desc.capitalize()} admin account '{username}'. Status: Success",
                    actor_role="Admin"
                )

                # NOTIFICATION: Superadmin Privileges Changed
                send_admin_notifications(
                    request, 
                    "update", 
                    username, 
                    f"has {action_desc} {username}."
                )

                messages.success(request, f"Superadmin privileges have been {action_desc} '{username}'.")
                return redirect("manage_admin_app:admin_list")
    
    messages.error(request, f"Update failed. The database rejected the change.")
    return redirect("manage_admin_app:admin_list")


@superadmin_required
def admin_toggle_active_view(request, username):
    """Toggles the is_active status."""
    get_resp = services.get_admin_by_username(username)
    admin_data = getattr(get_resp, "data", [])
    if not admin_data:
        messages.error(request, "Admin not found.")
        return redirect("manage_admin_app:admin_list")

    admin = admin_data[0]
    
    raw_val = admin.get("is_active")
    if raw_val is None:
        current_status = True
    elif isinstance(raw_val, bool):
        current_status = raw_val
    else:
        current_status = str(raw_val).lower() in ('true', '1', 't')

    new_status = not current_status
    # Professional phrasing for the message
    action_desc = "activated the account for" if new_status else "deactivated the account for"
    simple_action = "activated" if new_status else "deactivated"

    resp = services.update_admin(username, {"is_active": new_status})
    
    data = getattr(resp, "data", [])
    success = bool(data) and len(data) > 0

    actor = f"{request.session.get('admin_first_name', 'Unknown')} ({request.session.get('admin_username', '-')})"
    logs_services.create_log(
        actor,
        "Account",
        f"{simple_action.capitalize()} admin account '{username}'. Status: {'Success' if success else 'Failed'}",
        actor_role="Admin"
    )

    if success:
        # NOTIFICATION: Account Activated/Deactivated
        send_admin_notifications(
            request, 
            "status_change", 
            username, 
            f"has {action_desc} {username}."
        )

        messages.success(request, f"Admin '{username}' has been {simple_action}.")
    else:
        messages.error(request, f"Failed to update status for '{username}'.")

    return redirect("manage_admin_app:admin_list")


@superadmin_required
def admin_delete_view(request, username):
    """Deletes an admin."""
    get_resp = services.get_admin_by_username(username)
    admin_data = getattr(get_resp, "data", [])
    
    if not admin_data:
        messages.error(request, "Admin not found.")
        return redirect("manage_admin_app:admin_list")

    if username == request.session.get('admin_username'):
        messages.error(request, "You cannot delete your own account.")
        return redirect("manage_admin_app:admin_list")

    resp = services.delete_admin(username)
    success = is_success(resp)

    actor = f"{request.session.get('admin_first_name', 'Unknown')} ({request.session.get('admin_username', '-')})"
    logs_services.create_log(
        actor,
        "Account",
        f"Deleted admin account '{username}'. Status: {'Success' if success else 'Failed'}",
        actor_role="Admin"
    )

    if success:
        # NOTIFICATION: Admin Deleted
        send_admin_notifications(
            request, 
            "delete", 
            username, 
            f"has permanently deleted the administrator account for {username}."
        )

        messages.success(request, f"Admin '{username}' has been deleted.")
    else:
        messages.error(request, f"Failed to delete admin '{username}'.")

    return redirect("manage_admin_app:admin_list")


@superadmin_required
def admin_reset_password_view(request, username):
    """Resets password."""
    temp_pw = generate_temp_password()
    hashed_pw = hash_password(temp_pw)
    resp = services.update_admin(username, {"password": hashed_pw, "is_temp_password": True})
    success = is_success(resp)

    actor = f"{request.session.get('admin_first_name', 'Unknown')} ({request.session.get('admin_username', '-')})"
    logs_services.create_log(
        actor,
        "Security",
        f"Reset password for admin '{username}'. Status: {'Success' if success else 'Failed'}",
        actor_role="Admin"
    )

    if success:
        # NOTIFICATION: Password Reset
        send_admin_notifications(
            request, 
            "security", 
            username, 
            f"has triggered a security password reset for {username}."
        )

        messages.success(request, f"Password for '{username}' reset to temporary password '{temp_pw}'.")
    else:
        messages.error(request, f"Failed to reset password for '{username}'.")

    return redirect("manage_admin_app:admin_list")