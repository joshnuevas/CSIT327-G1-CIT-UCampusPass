# manage_staff_app/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import StaffCreateForm, StaffEditForm
from .helpers import generate_staff_username, hash_password
from . import services

# Simple permission decorator
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.session.get("admin_username") or request.session.get("user_is_superadmin"):
            return view_func(request, *args, **kwargs)
        messages.error(request, "You must be an admin to access this page.")
        return redirect("login_app:login")
    return wrapper

@admin_required
def staff_list_view(request):
    resp = services.list_staff(limit=500)
    staff = getattr(resp, "data", []) or []
    return render(request, "manage_staff_app/staff_list.html", {"staff_list": staff})

@admin_required
def staff_create_view(request):
    if request.method == "POST":
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            existing_count = len(getattr(services.list_staff(limit=1000), "data", []) or [])
            username = generate_staff_username(data['first_name'], data['last_name'], existing_count)
            temp_pw = "123456"
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

            if getattr(resp, "status_code", None) in (200, 201) or getattr(resp, "data", None):
                messages.success(request, f"Staff created: {username}.")
                return redirect("manage_staff_app:staff_list")
            else:
                messages.error(request, "Failed to create staff. Check logs.")
    else:
        form = StaffCreateForm()

    return render(request, "manage_staff_app/staff_form.html", {"form": form})

@admin_required
def staff_edit_view(request, username):
    get_resp = services.get_staff_by_username(username)
    staff_data = getattr(get_resp, "data", [])
    if not staff_data:
        messages.error(request, "Staff not found.")
        return redirect("manage_staff_app:staff_list")

    staff = staff_data[0]
    if request.method == "POST":
        form = StaffEditForm(request.POST)
        if form.is_valid():
            updates = form.cleaned_data
            resp = services.update_staff(username, updates)
            if getattr(resp, "status_code", None) == 200 or getattr(resp, "data", None):
                messages.success(request, "Staff updated.")
                return redirect("manage_staff_app:staff_list")
            else:
                messages.error(request, "Failed to update staff.")
    else:
        initial = {
            "first_name": staff.get("first_name"),
            "last_name": staff.get("last_name"),
            "email": staff.get("email"),
            "contact_number": staff.get("contact_number"),
            "is_active": staff.get("is_active", True)
        }
        form = StaffEditForm(initial=initial)

    return render(request, "manage_staff_app/staff_form.html", {"form": form, "editing": True, "username": username})

@admin_required
def staff_deactivate_view(request, username):
    resp = services.deactivate_staff(username)
    if getattr(resp, "status_code", None) == 200 or getattr(resp, "data", None):
        messages.success(request, "Staff deactivated.")
    else:
        messages.error(request, "Failed to deactivate staff.")
    return redirect("manage_staff_app:staff_list")

@admin_required
def staff_reset_password_view(request, username):
    temp_pw = "123456"
    hashed = hash_password(temp_pw)
    resp = services.update_staff(username, {"password": hashed, "is_temp_password": True})
    if getattr(resp, "status_code", None) == 200 or getattr(resp, "data", None):
        messages.success(request, f"Password reset. Temporary password is set to '{temp_pw}'.")
    else:
        messages.error(request, "Failed to reset password.")
    return redirect("manage_staff_app:staff_list")
