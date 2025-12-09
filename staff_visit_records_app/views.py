# staff_visit_records_app/views.py
from datetime import datetime, time as dtime

import pytz
from django.contrib import messages
from django.db.models import Q, Case, When, IntegerField
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from dashboard_app.views import staff_required, apply_nine_pm_cutoff
from dashboard_app.models import Visit, SystemLog

PH_TZ = pytz.timezone("Asia/Manila")

@staff_required
def staff_visit_records_view(request):
    """
    Staff Visit Records
    ...
    """

    # 🔁 Global 9PM cutoff (persists updates to Supabase)
    apply_nine_pm_cutoff()

    now_ph = timezone.now().astimezone(PH_TZ)
    today = now_ph.date()

    # GET parameters
    filter_submitted = request.GET.get("filter_submitted")
    filter_date_str = (request.GET.get("date") or "").strip()
    filter_query = (request.GET.get("q") or "").strip()
    status_filter = (request.GET.get("status") or "all").lower().strip()

    # ----------------------
    # 1. Determine which date to show
    # ----------------------
    if filter_submitted:
        if filter_date_str:
            try:
                filter_date = datetime.strptime(filter_date_str, "%Y-%m-%d").date()
            except ValueError:
                filter_date = today
        else:
            filter_date = today
    else:
        filter_date = today

    # ----------------------
    # 2. Base queryset (specific date)
    # ----------------------
    qs = Visit.objects.filter(visit_date=filter_date)

    # ----------------------
    # 3. Apply search filter
    # ----------------------
    if filter_query:
        qs = qs.filter(
            Q(code__icontains=filter_query)
            | Q(department__icontains=filter_query)
            | Q(purpose__icontains=filter_query)
            | Q(user_email__icontains=filter_query)
        )

    # ----------------------
    # 4. Apply status filter (from pills)
    # ----------------------
    status_map = {
        "upcoming": "Upcoming",
        "active": "Active",
        "completed": "Completed",
        "expired": "Expired",
    }

    if status_filter in status_map:
        qs = qs.filter(status=status_map[status_filter])

    # ----------------------
    # 5. Sorting – Active → Upcoming → Completed → Expired
    # ----------------------
    status_priority = Case(
        When(status="Active", then=0),
        When(status="Upcoming", then=1),
        When(status="Completed", then=2),
        When(status="Expired", then=3),
        default=4,
        output_field=IntegerField(),
    )

    visits = (
        qs
        .annotate(status_priority=status_priority)
        .order_by(
            "status_priority",   # custom priority order
            "visit_date",        # then by date
            "start_time",        # then by time
            "code",              # stable tie-breaker
        )
    )

    # ----------------------
    # 6. Summary label (matches My Passes UI)
    # ----------------------
    filter_mode_text = "Selected Date"

    if filter_date == today:
        filter_date_display = "Today"
    else:
        filter_date_display = filter_date.strftime("%B %d, %Y")

    return render(
        request,
        "staff_visit_records_app/staff_visit_records.html",
        {
            "visits": visits,
            "today": today,
            "filter_date": filter_date.strftime("%Y-%m-%d"),
            "filter_query": filter_query,
            "status_filter": status_filter,
            "filter_mode_text": filter_mode_text,
            "filter_date_display": filter_date_display,
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
