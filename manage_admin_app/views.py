# manage_admin_app/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from . import services
from .forms import AdminCreateForm, AdminEditForm
from .helpers import hash_password, generate_admin_username, generate_temp_password
from manage_staff_app.views import admin_required


@admin_required
def admin_list_view(request):
    """
    Display the list of administrators.
    """
    resp = services.list_admins(limit=500)
    admins = getattr(resp, "data", []) or []
    return render(request, "manage_admin_app/admin_list.html", {"admin_list": admins})


@admin_required
def admin_create_view(request):
    """
    Create a new administrator with auto-generated username and temporary password.
    """
    if request.method == "POST":
        form = AdminCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            # Generate unique username
            resp_list = services.list_admins(limit=500)
            existing_count = len(getattr(resp_list, "data", []) or [])
            username = generate_admin_username(data['first_name'], data['last_name'], existing_count)

            # Generate fixed temporary password
            temp_pw = generate_temp_password()
            hashed_pw = hash_password(temp_pw)

            # Prepare record for Supabase
            record = {
                **data,
                "username": username,
                "password": hashed_pw,
                "is_temp_password": True,
                "is_active": True
            }

            # Create admin
            resp = services.create_admin(record)

            # Success check based on resp.data
            if getattr(resp, "data", None) and len(resp.data) > 0:
                messages.success(request, f"Admin '{username}' created with temporary password '{temp_pw}'.")
                return redirect("manage_admin_app:admin_list")
            else:
                print(resp)
                messages.error(request, f"Failed to create admin. Supabase response: {resp}")
                return redirect("manage_admin_app:admin_create")
        else:
            messages.error(request, f"Invalid form data: {form.errors}")
            return redirect("manage_admin_app:admin_create")
    else:
        form = AdminCreateForm()

    return render(request, "manage_admin_app/admin_form.html", {"form": form})


@admin_required
def admin_edit_view(request, username):
    """
    Edit an existing administrator.
    """
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
            resp = services.update_admin(username, updates)

            updated = getattr(resp, "data", None)
            if updated and len(updated) > 0:
                messages.success(request, f"Admin '{username}' updated successfully.")
            else:
                print(resp)
                messages.error(request, f"Failed to update admin. Supabase response: {resp}")

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


@admin_required
def admin_toggle_active_view(request, username):
    """
    Toggle an admin's active/inactive status.
    """
    get_resp = services.get_admin_by_username(username)
    admin_data = getattr(get_resp, "data", [])
    if not admin_data:
        messages.error(request, "Admin not found.")
        return redirect("manage_admin_app:admin_list")

    admin = admin_data[0]
    current_status = admin.get("is_active", True)
    new_status = not current_status
    action = "activated" if new_status else "deactivated"

    resp = services.update_admin(username, {"is_active": new_status})

    if getattr(resp, "status_code", None) in (200, 201) or getattr(resp, "data", None):
        messages.success(request, f"Admin '{username}' has been {action}.")
    else:
        messages.error(request, f"Failed to update status for '{username}'.")

    return redirect("manage_admin_app:admin_list")


@admin_required
def admin_reset_password_view(request, username):
    """
    Reset an administrator's password to the fixed temporary password.
    """
    temp_pw = generate_temp_password()
    hashed = hash_password(temp_pw)
    resp = services.update_admin(username, {"password": hashed, "is_temp_password": True})

    if getattr(resp, "status_code", None) in (200, 201) or getattr(resp, "data", None):
        messages.success(request, f"Password for '{username}' reset to temporary password '{temp_pw}'.")
    else:
        messages.error(request, f"Failed to reset password for '{username}'.")

    return redirect("manage_admin_app:admin_list")
