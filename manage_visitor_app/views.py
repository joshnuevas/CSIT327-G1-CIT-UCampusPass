from django.shortcuts import render, redirect
from django.contrib import messages
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

    if hasattr(resp, 'data') and resp.data:
        return True
    if hasattr(resp, 'status_code') and resp.status_code in (200, 201, 204):
        return True
        
    return False

# ===== NOTIFICATION HELPER =====
def send_visitor_admin_notifications(request, visitor_id, description):
    """
    Notify other admins when a visitor account is managed (removed/deactivated).
    """
    try:
        current_admin_username = request.session.get('admin_username')
        actor_name = request.session.get('admin_first_name', current_admin_username)
        
        # Fetch all admins
        all_admins = Administrator.objects.all()
        
        for admin in all_admins:
            # Don't notify the actor
            if admin.username == current_admin_username:
                continue

            # Notify everyone else
            create_notification(
                receiver_admin=admin,
                title="Visitor Account Alert",
                message=f"{actor_name} {description}",
                type="system_alert"
            )
    except Exception as e:
        print(f"Error sending visitor notifications: {e}")

# ===== DECORATOR =====
def admin_required(view_func):
    """Decorator to restrict access to admins."""
    def wrapper(request, *args, **kwargs):
        if request.session.get("admin_username") or request.session.get("user_is_superadmin"):
            return view_func(request, *args, **kwargs)
        messages.error(request, "You must be an admin to access this page.")
        return redirect("login_app:login")
    return wrapper

# ===== VIEWS =====

@admin_required
def visitor_list_view(request):
    """Display all registered visitors from the users table."""
    resp = services.list_visitors(limit=500)
    visitors = getattr(resp, "data", []) or []
    return render(request, "manage_visitor_app/visitor_list.html", {"visitors": visitors})

@admin_required
def visitor_deactivate_view(request, user_id):
    """Deactivate or remove a visitor account and log the action."""
    
    # 1. Fetch email BEFORE deletion so we can use it in the notification
    visitor_email = f"ID {user_id}" # Fallback if fetch fails
    try:
        profile_resp = services.get_visitor_by_id(user_id)
        if is_success(profile_resp) and profile_resp.data:
            # Safely get email from the first result
            visitor_email = profile_resp.data[0].get('email', visitor_email)
    except Exception as e:
        print(f"Could not fetch visitor email before deletion: {e}")

    # 2. Perform Deletion
    resp = services.deactivate_visitor(user_id)

    # Use the robust check
    success = is_success(resp)

    # ===== Log the action =====
    actor = f"{request.session.get('admin_first_name', 'Unknown')} ({request.session.get('admin_username', '-')})"
    logs_services.create_log(
        actor,
        "Visitor Management",
        f"Removed visitor account ({visitor_email}). Status: {'Success' if success else 'Failed'}",
        actor_role="Admin"
    )

    if success:
        # 🔔 Notify other admins using the Email
        send_visitor_admin_notifications(
            request,
            user_id,
            f"has removed visitor account {visitor_email}."
        )

        messages.success(request, f"Visitor account ({visitor_email}) has been removed.")
    else:
        messages.error(request, f"Failed to remove visitor {visitor_email}. Check system logs.")

    return redirect("manage_visitor_app:visitor_list")

# ===== NEW: VISITOR DETAIL VIEW =====
@admin_required
def visitor_detail(request, user_id):
    """
    Fetch specific visitor details and their visit history.
    """
    # 1. Fetch the Visitor Profile
    # We expect services.get_visitor_by_id to return a Supabase response
    profile_resp = services.get_visitor_by_id(user_id)
    
    if not is_success(profile_resp) or not profile_resp.data:
        messages.error(request, "Visitor not found or database error.")
        return redirect("manage_visitor_app:visitor_list")
    
    # Supabase returns a list, take the first item
    visitor = profile_resp.data[0]

    # 2. Fetch Visit History
    history_resp = services.get_visitor_history(user_id)
    visit_history = getattr(history_resp, "data", []) or []

    # 3. Determine if there is an active/current visit (optional helper for UI)
    current_visit = None
    if visit_history:
        # Assuming the history is ordered by date descending
        latest = visit_history[0]
        # Check if status is Active, Checked In, or Upcoming
        if latest.get('status') in ['Active', 'Checked In', 'Upcoming']:
            current_visit = latest

    context = {
        "visitor": visitor,
        "visit_history": visit_history,
        "current_visit": current_visit
    }

    return render(request, "manage_visitor_app/visitor_detail.html", context)