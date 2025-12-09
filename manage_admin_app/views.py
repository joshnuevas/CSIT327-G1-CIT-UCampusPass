from django.shortcuts import render, redirect
from django.contrib import messages
from . import services
from .forms import AdminCreateForm, AdminEditForm
from .helpers import hash_password, generate_admin_username, generate_temp_password
from manage_reports_logs_app import services as logs_services

# ===== Helper for Supabase Response Checking =====
def is_success(resp):
    """
    Checks if a Supabase response was successful.
    1. Checks if there is a wrapper 'error' attribute.
    2. Returns True if no error is found.
    """
    # Check for client-side wrapper error
    if hasattr(resp, 'error') and resp.error:
        print(f"Supabase Error: {resp.error}") # DEBUG: Print error to console
        return False
        
    # Check if the response body contains an error code (PostgREST style)
    # Sometimes resp.data can be a dict with 'code' and 'message' on failure
    data = getattr(resp, "data", None)
    if isinstance(data, dict) and 'code' in data and 'message' in data:
         print(f"Supabase Data Error: {data}")
         return False

    return True

# ===== PERMISSION DECORATOR =====
def superadmin_required(view_func):
    def wrapper(request, *args, **kwargs):
        # Ensure session value is treated as boolean
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
                "is_superadmin": False # Default to False explicitly
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

            # Preserve is_active if the edit form did not include the field in POST
            # (some templates render a simplified edit form and omit the checkbox)
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
    """
    Toggles the is_superadmin status.
    Updated to handle RLS silence and debug database rejection.
    """
    # 1. Fetch current status
    get_resp = services.get_admin_by_username(username)
    admin_data = getattr(get_resp, "data", [])
    
    if not admin_data:
        messages.error(request, "Admin not found.")
        return redirect("manage_admin_app:admin_list")

    admin = admin_data[0]
    
    # 2. Determine boolean status safely
    raw_status = admin.get("is_superadmin")
    if isinstance(raw_status, bool):
        current_status = raw_status
    else:
        # Handle string 'true'/'false' or None
        current_status = str(raw_status).lower() in ('true', '1', 't')

    new_status = not current_status
    action = "granted superadmin privileges to" if new_status else "revoked superadmin privileges from"
    
    # 3. Perform Update
    print(f"DEBUG: Attempting to set {username} superadmin to {new_status}")
    resp = services.update_admin(username, {"is_superadmin": new_status})
    
    # 4. Robust Success Check (Replaced strict len(data) check)
    # We use is_success() because RLS might update the row but block returning the data.
    if is_success(resp):
        # Optional: Double verify if the update stuck (Best practice for permissions)
        verify_resp = services.get_admin_by_username(username)
        verify_data = getattr(verify_resp, "data", [])
        
        # Verify the DB actually has the new value
        if verify_data:
            db_val = verify_data[0].get("is_superadmin")
            # Normalize DB value
            db_bool = db_val if isinstance(db_val, bool) else str(db_val).lower() in ('true', '1', 't')
            
            if db_bool == new_status:
                actor = f"{request.session.get('admin_first_name', 'Unknown')} ({request.session.get('admin_username', '-')})"
                logs_services.create_log(
                    actor,
                    "Account",
                    f"{action.capitalize()} admin account '{username}'. Status: Success",
                    actor_role="Admin"
                )
                messages.success(request, f"Superadmin privileges have been {action} '{username}'.")
                return redirect("manage_admin_app:admin_list")
    
    # Print the type and the full content of 'resp' to see what it actually holds
    print(f"DEBUG: Type of resp: {type(resp)}")
    print(f"DEBUG: Full resp object: {resp}")

    # Existing logic (keep this for now until we see the logs)
    error_msg = getattr(resp, 'error', 'Unknown Database Error')
    print(f"DEBUG: Update Failed. Response Error: {error_msg}")
    
    messages.error(request, f"Update failed. The database rejected the change. Check your server console for Supabase error details.")
    return redirect("manage_admin_app:admin_list")

@superadmin_required
def admin_toggle_active_view(request, username):
    """
    Toggles the is_active status.
    Fix: Strictly checks if the update query returned a modified row.
    """
    get_resp = services.get_admin_by_username(username)
    admin_data = getattr(get_resp, "data", [])
    if not admin_data:
        messages.error(request, "Admin not found.")
        return redirect("manage_admin_app:admin_list")

    admin = admin_data[0]
    
    # Handle Boolean/None types safely
    raw_val = admin.get("is_active")
    if raw_val is None:
        current_status = True # Default from schema
    elif isinstance(raw_val, bool):
        current_status = raw_val
    else:
        current_status = str(raw_val).lower() in ('true', '1', 't')

    new_status = not current_status
    action = "activated" if new_status else "deactivated"

    resp = services.update_admin(username, {"is_active": new_status})
    
    # Strict check
    data = getattr(resp, "data", [])
    success = bool(data) and len(data) > 0

    actor = f"{request.session.get('admin_first_name', 'Unknown')} ({request.session.get('admin_username', '-')})"
    logs_services.create_log(
        actor,
        "Account",
        f"{action.capitalize()} admin account '{username}'. Status: {'Success' if success else 'Failed'}",
        actor_role="Admin"
    )

    if success:
        messages.success(request, f"Admin '{username}' has been {action}.")
    else:
        messages.error(request, f"Failed to update status for '{username}'.")

    return redirect("manage_admin_app:admin_list")

@superadmin_required
def admin_delete_view(request, username):
    """Deletes an admin."""
    # 1. Fetch to confirm exists
    get_resp = services.get_admin_by_username(username)
    admin_data = getattr(get_resp, "data", [])
    
    if not admin_data:
        messages.error(request, "Admin not found.")
        return redirect("manage_admin_app:admin_list")

    # 2. Prevent self-deletion
    if username == request.session.get('admin_username'):
        messages.error(request, "You cannot delete your own account.")
        return redirect("manage_admin_app:admin_list")

    # 3. Perform Delete
    resp = services.delete_admin(username)
    
    # Supabase Delete Success Check
    # Usually returns the deleted row in 'data'. If 'data' has items, it succeeded.
    success = is_success(resp)

    actor = f"{request.session.get('admin_first_name', 'Unknown')} ({request.session.get('admin_username', '-')})"
    logs_services.create_log(
        actor,
        "Account",
        f"Deleted admin account '{username}'. Status: {'Success' if success else 'Failed'}",
        actor_role="Admin"
    )

    if success:
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
        messages.success(request, f"Password for '{username}' reset to temporary password '{temp_pw}'.")
    else:
        messages.error(request, f"Failed to reset password for '{username}'.")

    return redirect("manage_admin_app:admin_list")