# staff_visit_records_app/views.py
import json
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from dashboard_app.views import staff_required
from . import services
from supabase import create_client
from django.conf import settings
from datetime import datetime
import pytz
from django.utils import timezone

# Initialize Supabase
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

@staff_required
def staff_visit_records_view(request):
    from datetime import date
    visits = services.get_all_visits(limit=2000) or []

    # Categorize visits
    categorized_visits = services.categorize_visits(visits)

    # Convert to JSON for the template
    visits_json = json.dumps(categorized_visits, default=str)

    return render(request, "staff_visit_records_app/staff_visit_records.html", {
        "categorized_visits": categorized_visits,
        "visits_json": visits_json,
        "today": timezone.now().astimezone(pytz.timezone('Asia/Manila')).date().isoformat(),
    })

@staff_required
@require_POST
def check_in_visitor(request):
    """Check in a visitor from the visit records page"""
    visit_id = request.POST.get('visit_id')
    staff_username = request.session['staff_username']
    staff_first_name = request.session.get('staff_first_name', 'Staff')

    if not visit_id:
        messages.error(request, "Invalid visit ID.")
        return redirect('staff_visit_records_app:staff_visit_records')

    try:
        # Get visit details
        visit_resp = supabase.table("visits").select("*").eq("visit_id", visit_id).execute()

        if not visit_resp.data:
            messages.error(request, f'Visit not found.')
            return redirect('staff_visit_records_app:staff_visit_records')

        visit = visit_resp.data[0]

        # Check if visit can be checked in
        if visit['status'] != 'Upcoming':
            messages.warning(request, f'Visit is already {visit["status"]}. Cannot check in.')
            return redirect('staff_visit_records_app:staff_visit_records')

        # Get current time in Philippines timezone
        PHILIPPINES_TZ = pytz.timezone('Asia/Manila')
        current_time = datetime.now(PHILIPPINES_TZ)
        checkin_time = current_time.strftime('%H:%M:%S')

        # Update visit status to Active and set start_time
        supabase.table("visits").update({
            "status": "Active",
            "start_time": checkin_time
        }).eq("visit_id", visit_id).execute()

        # Create log entry
        log_entry = {
            "actor": f"{staff_first_name} ({staff_username})",
            "action_type": "Visitor Check-In",
            "description": f"Checked in visitor with code {visit['code']} for {visit['purpose']} at {visit['department']}",
            "actor_role": "Staff",
            "created_at": current_time.isoformat()
        }
        supabase.table("system_logs").insert(log_entry).execute()

        messages.success(request, f'✅ Visitor checked in successfully! Code: {visit["code"]}')
        return redirect('staff_visit_records_app:staff_visit_records')

    except Exception as e:
        messages.error(request, "An error occurred during check-in.")
        return redirect('staff_visit_records_app:staff_visit_records')

@staff_required
@require_POST
def check_out_visitor(request):
    """Check out a visitor from the visit records page"""
    visit_id = request.POST.get('visit_id')
    staff_username = request.session['staff_username']
    staff_first_name = request.session.get('staff_first_name', 'Staff')

    if not visit_id:
        messages.error(request, "Invalid visit ID.")
        return redirect('staff_visit_records_app:staff_visit_records')

    try:
        # Get visit details
        visit_resp = supabase.table("visits").select("*").eq("visit_id", visit_id).execute()

        if not visit_resp.data:
            messages.error(request, f'Visit not found.')
            return redirect('staff_visit_records_app:staff_visit_records')

        visit = visit_resp.data[0]

        # Check if visit can be checked out
        if visit['status'] != 'Active':
            messages.warning(request, f'Visit is {visit["status"]}. Cannot check out.')
            return redirect('staff_visit_records_app:staff_visit_records')

        # Get current time in Philippines timezone
        PHILIPPINES_TZ = pytz.timezone('Asia/Manila')
        current_time = datetime.now(PHILIPPINES_TZ)
        checkout_time = current_time.strftime('%H:%M:%S')

        # Update visit status to Completed and set end_time
        supabase.table("visits").update({
            "status": "Completed",
            "end_time": checkout_time
        }).eq("visit_id", visit_id).execute()

        # Create log entry
        log_entry = {
            "actor": f"{staff_first_name} ({staff_username})",
            "action_type": "Visitor Check-Out",
            "description": f"Checked out visitor with code {visit['code']} from {visit['department']} at {checkout_time}",
            "actor_role": "Staff",
            "created_at": current_time.isoformat()
        }
        supabase.table("system_logs").insert(log_entry).execute()

        messages.success(request, f'✅ Visitor checked out successfully at {current_time.strftime("%I:%M %p")}! Code: {visit["code"]}')
        return redirect('staff_visit_records_app:staff_visit_records')

    except Exception as e:
        messages.error(request, "An error occurred during check-out.")
        return redirect('staff_visit_records_app:staff_visit_records')
