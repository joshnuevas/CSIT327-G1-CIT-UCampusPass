from datetime import datetime, date, timedelta

import pytz
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from dashboard_app.models import Visit, SystemLog
from register_app.models import User


def history_view(request):
    """
    Visitor 'My Passes' page.

    Default behavior:
      - Only show visits from (today - 7 days) up to (today + 7 days).

    Rules:
      - Auto-expire visits whose date is already past today
        (Upcoming/Active -> Expired).
      - Filter by:
          * Date (any past date, but not beyond today + 7 days)
          * Search query (code or department)
          * Status (All / Active / Upcoming / Completed (Completed + Expired))
    """

    # ---------- AUTH CHECK ----------
    if "user_email" not in request.session:
        return redirect("login_app:login")

    user_email = request.session["user_email"]

    # ---------- TIME CONTEXT ----------
    philippines_tz = pytz.timezone("Asia/Manila")
    now_ph = datetime.now(philippines_tz)
    today = now_ph.date()
    max_allowed_date = today + timedelta(days=7)  # same as booking limit

    # ---------- AUTO-EXPIRE OLD VISITS ----------
    Visit.objects.filter(
        user_email=user_email,
        visit_date__lt=today,
        status__in=["Upcoming", "Active"],
    ).update(status="Expired")

    # ---------- DEFAULT WINDOW (LAST 7 DAYS → NEXT 7 DAYS) ----------
    default_start_date = today - timedelta(days=7)
    default_end_date = max_allowed_date

    # ---------- READ FILTER PARAMS ----------
    date_str = (request.GET.get("date") or "").strip()
    search_query = (request.GET.get("q") or "").strip()
    status_filter = (request.GET.get("status") or "").strip().lower()
    filter_submitted = request.GET.get("filter_submitted") == "1"

    # Base queryset: all visits for this user
    visits_qs = Visit.objects.filter(user_email=user_email)

    filter_mode_text = ""
    filter_date_display = ""
    filter_date_value = ""

    # Warn only if the user actually hit “Apply Filters” with nothing set
    if filter_submitted and not date_str and not search_query and not status_filter:
        messages.warning(
            request,
            "Please enter a visit date, search keyword, or select a status before applying filters."
        )

    # ---------- DATE FILTER ----------
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = today

        # Clamp only the *future* side (cannot see beyond +7 days from today)
        if selected_date > max_allowed_date:
            selected_date = max_allowed_date

        visits_qs = visits_qs.filter(visit_date=selected_date)

        filter_mode_text = "Showing visits for"
        filter_date_display = selected_date.strftime("%b %d, %Y")
        filter_date_value = selected_date.isoformat()
    else:
        # DEFAULT: last 7 days up to next 7 days
        visits_qs = visits_qs.filter(
            visit_date__gte=default_start_date,
            visit_date__lte=default_end_date,
        )
        filter_mode_text = "Showing visits from"
        filter_date_display = (
            f"{default_start_date.strftime('%b %d, %Y')} "
            f"to {default_end_date.strftime('%b %d, %Y')}"
        )

    # Safety: never show anything beyond +7 days ahead
    visits_qs = visits_qs.filter(visit_date__lte=max_allowed_date)

    # ---------- TEXT SEARCH ----------
    if search_query:
        visits_qs = visits_qs.filter(
            Q(code__icontains=search_query) |
            Q(department__icontains=search_query) |
            Q(purpose__icontains=search_query)
        )

    # ---------- STATUS FILTER (Active / Upcoming / Completed) ----------
    # "Completed" here means both Completed and Expired passes
    if status_filter == "active":
        visits_qs = visits_qs.filter(status__iexact="Active")
    elif status_filter == "upcoming":
        visits_qs = visits_qs.filter(status__iexact="Upcoming")
    elif status_filter == "completed":
        visits_qs = visits_qs.filter(status__in=["Completed", "Expired"])
    # else: show all statuses

    # ---------- ORDERING ----------
    visits_qs = visits_qs.order_by("-visit_date", "-start_time")

    # ---------- FORMAT DISPLAY FIELDS ----------
    visits = []
    for visit in visits_qs:
        visit_date_obj = visit.visit_date

        # Friendly date label
        if visit_date_obj == today:
            visit.display_date = f"Today, {visit_date_obj.strftime('%b %d')}"
        else:
            visit.display_date = visit_date_obj.strftime("%b %d, %Y")

        # Times
        if visit.start_time:
            visit.formatted_start_time = visit.start_time.strftime("%I:%M %p")
        else:
            visit.formatted_start_time = "Not checked in"

        if visit.end_time:
            visit.formatted_end_time = visit.end_time.strftime("%I:%M %p")
        else:
            visit.formatted_end_time = "Pending"

        visits.append(visit)

    context = {
        "user_email": user_email,
        "user_first_name": request.session.get("user_first_name"),
        "visits": visits,
        "filter_date": filter_date_value,
        "filter_query": search_query,
        "filter_mode_text": filter_mode_text,
        "filter_date_display": filter_date_display,
        "today": today,
        "status_filter": status_filter,  # for highlighting the active pill in the template
    }

    return render(request, "history_app/history.html", context)


@require_POST
def cancel_visit(request):
    """
    Cancels a visit for the current user.

    - Verifies the user is logged in.
    - Ensures the visit belongs to the current user.
    - Deletes the visit and logs the action in SystemLog.
    - Redirects back to Dashboard or History depending on where it was triggered.
    """
    # ---------- AUTH CHECK ----------
    if "user_email" not in request.session:
        return redirect("login_app:login")

    user_email = request.session["user_email"]

    # From which page did this come?
    # Dashboard forms should send: <input type="hidden" name="from_dashboard" value="1">
    from_dashboard = request.POST.get("from_dashboard") == "1"

    def _redirect_back():
        """Helper: go back to the correct page."""
        if from_dashboard:
            return redirect("dashboard_app:dashboard")
        return redirect("history_app:visit_history")

    # ---------- GET VISIT ID ----------
    visit_id = request.POST.get("visit_id")
    if not visit_id:
        messages.error(request, "Invalid visit ID.")
        return _redirect_back()

    try:
        # ---------- FETCH VISIT (AND VERIFY OWNERSHIP) ----------
        try:
            visit = Visit.objects.get(visit_id=visit_id, user_email=user_email)
        except Visit.DoesNotExist:
            messages.error(
                request,
                "Visit not found or you do not have permission to cancel this visit."
            )
            return _redirect_back()

        visit_code = visit.code or "N/A"
        visit_date = visit.visit_date or "N/A"
        department = visit.department or "N/A"

        # ---------- DELETE VISIT ----------
        visit.delete()

        # ---------- LOG THE CANCELLATION ----------
        philippines_tz = pytz.timezone("Asia/Manila")
        current_time = datetime.now(philippines_tz)

        SystemLog.objects.create(
            actor=user_email,
            action_type="Visit Cancelled",
            description=(
                f"User cancelled visit {visit_code} "
                f"scheduled for {visit_date} at {department}"
            ),
            actor_role="Visitor",
            created_at=current_time,
        )

        messages.success(request, "Visit cancelled successfully.")

    except Exception as e:
        messages.error(
            request,
            f"An error occurred while cancelling the visit: {str(e)}",
        )

    # ---------- FINAL REDIRECT ----------
    return _redirect_back()
