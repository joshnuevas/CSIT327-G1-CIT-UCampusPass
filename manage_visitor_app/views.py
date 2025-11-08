from django.shortcuts import render, redirect
from django.contrib import messages
from . import services
from manage_reports_logs_app import services as logs_services

def admin_required(view_func):
    """Decorator to restrict access to admins."""
    def wrapper(request, *args, **kwargs):
        if request.session.get("admin_username") or request.session.get("user_is_superadmin"):
            return view_func(request, *args, **kwargs)
        messages.error(request, "You must be an admin to access this page.")
        return redirect("login_app:login")
    return wrapper


@admin_required
def visitor_list_view(request):
    """Display all registered visitors from the users table."""
    resp = services.list_visitors(limit=500)
    visitors = getattr(resp, "data", []) or []
    return render(request, "manage_visitor_app/visitor_list.html", {"visitors": visitors})


@admin_required
def visitor_deactivate_view(request, user_id):
    """Deactivate or remove a visitor account and log the action."""
    resp = services.deactivate_visitor(user_id)

    # ===== Determine success based on Supabase v2 APIResponse =====
    success = bool(getattr(resp, "data", []))  # True if row was deleted, False otherwise

    # ===== Log the attempt (always create log) =====
    actor = f"{request.session.get('admin_first_name', 'Unknown')} ({request.session.get('admin_username', '-')})"
    logs_services.create_log(
        actor=actor,
        action_type="Account",
        description=f"Attempted to remove visitor account with ID {user_id}. Status: {'Success' if success else 'Failed'}",
        actor_role="Admin"
    )

    # ===== Show message to admin =====
    if success:
        messages.success(request, f"Visitor with ID {user_id} removed.")
    else:
        messages.error(request, f"Failed to remove visitor {user_id}.")

    return redirect("manage_visitor_app:visitor_list")
