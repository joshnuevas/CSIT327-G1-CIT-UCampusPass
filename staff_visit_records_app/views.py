# staff_visit_records_app/views.py
from datetime import datetime

import pytz
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from dashboard_app.views import staff_required
from dashboard_app.models import Visit, SystemLog


PH_TZ = pytz.timezone("Asia/Manila")


@staff_required
def staff_visit_records_view(request):
    """
    Staff Visit Records

    - Defaults to showing ONLY today's visits (PH time).
    - Supports the same date + search filters as the user "My Passes" page.
    - Shows ALL visits for that date (any status, any visitor).
    """
    today = timezone.now().astimezone(PH_TZ).date()

    filter_submitted = request.GET.get("filter_submitted")
    filter_date_str = (request.GET.get("date") or "").strip()
    filter_query = (request.GET.get("q") or "").strip()

    # --- Determine which date we're showing ---
    if filter_submitted:
        if filter_date_str:
            try:
                filter_date = datetime.strptime(filter_date_str, "%Y-%m-%d").date()
            except ValueError:
                filter_date = today
        else:
            filter_date = today
    else:
        filter_date = today  # initial load

    # --- Base queryset: ALL visits for that calendar date ---
    qs = Visit.objects.filter(visit_date=filter_date)

    # --- Search: code, department, purpose, email ---
    if filter_query:
        qs = qs.filter(
            Q(code__icontains=filter_query)
            | Q(department__icontains=filter_query)
            | Q(purpose__icontains=filter_query)
            | Q(user_email__icontains=filter_query)
        )

    # Order by start_time then code so the day reads nicely
    visits = qs.order_by("start_time", "code")

    return render(
        request,
        "staff_visit_records_app/staff_visit_records.html",
        {
            "visits": visits,
            "today": today,
            "filter_date": filter_date.strftime("%Y-%m-%d"),
            "filter_query": filter_query,
        },
    )


@staff_required
@require_POST
def check_in_visitor(request):
    """Check in a visitor from the visit records page."""
    visit_id = request.POST.get("visit_id")
    staff_username = request.session["staff_username"]
    staff_first_name = request.session.get("staff_first_name", "Staff")

    if not visit_id:
        messages.error(request, "Invalid visit ID.")
        return redirect("staff_visit_records_app:staff_visit_records")

    try:
        visit = Visit.objects.get(visit_id=visit_id)

        if visit.status != "Upcoming":
            messages.warning(
                request,
                f"Visit is already {visit.status}. Cannot check in.",
            )
            return redirect("staff_visit_records_app:staff_visit_records")

        current_time = timezone.now().astimezone(PH_TZ)
        checkin_time = current_time.time()

        visit.status = "Active"
        visit.start_time = checkin_time
        visit.save()

        SystemLog.objects.create(
            actor=f"{staff_first_name} ({staff_username})",
            action_type="Visitor Check-In",
            description=(
                f"Checked in visitor with code {visit.code} for "
                f"{visit.purpose} at {visit.department}"
            ),
            actor_role="Staff",
            created_at=current_time,
        )

        messages.success(
            request,
            f"✅ Visitor checked in successfully! Code: {visit.code}",
        )
        return redirect("staff_visit_records_app:staff_visit_records")

    except Visit.DoesNotExist:
        messages.error(request, "Visit not found.")
        return redirect("staff_visit_records_app:staff_visit_records")
    except Exception:
        messages.error(request, "An error occurred during check-in.")
        return redirect("staff_visit_records_app:staff_visit_records")


@staff_required
@require_POST
def check_out_visitor(request):
    """Check out a visitor from the visit records page."""
    visit_id = request.POST.get("visit_id")
    staff_username = request.session["staff_username"]
    staff_first_name = request.session.get("staff_first_name", "Staff")

    if not visit_id:
        messages.error(request, "Invalid visit ID.")
        return redirect("staff_visit_records_app:staff_visit_records")

    try:
        visit = Visit.objects.get(visit_id=visit_id)

        if visit.status != "Active":
            messages.warning(
                request,
                f"Visit is {visit.status}. Cannot check out.",
            )
            return redirect("staff_visit_records_app:staff_visit_records")

        current_time = timezone.now().astimezone(PH_TZ)
        checkout_time = current_time.time()

        visit.status = "Completed"
        visit.end_time = checkout_time
        visit.save()

        SystemLog.objects.create(
            actor=f"{staff_first_name} ({staff_username})",
            action_type="Visitor Check-Out",
            description=(
                f"Checked out visitor with code {visit.code} "
                f"from {visit.department} at {checkout_time}"
            ),
            actor_role="Staff",
            created_at=current_time,
        )

        messages.success(
            request,
            f"✅ Visitor checked out successfully at "
            f"{current_time.strftime('%I:%M %p')}! Code: {visit.code}",
        )
        return redirect("staff_visit_records_app:staff_visit_records")

    except Visit.DoesNotExist:
        messages.error(request, "Visit not found.")
        return redirect("staff_visit_records_app:staff_visit_records")
    except Exception:
        messages.error(request, "An error occurred during check-out.")
        return redirect("staff_visit_records_app:staff_visit_records")
