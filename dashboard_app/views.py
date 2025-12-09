# dashboard_app/views.py
from django.shortcuts import render, redirect
import os, json
from dotenv import load_dotenv
from datetime import datetime, date, timezone, timedelta, time as dtime
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now as django_now
import pytz
import logging
from django.contrib import messages
import random
import string

# Import Django models
from .models import Visit, SystemLog, AdminDismissedNotification
from login_app.models import Administrator, FrontDeskStaff
from register_app.models import User

# Import logs service
from manage_reports_logs_app.services import list_logs

# Setup logging
logger = logging.getLogger(__name__)

# Philippines timezone
PHILIPPINES_TZ = pytz.timezone('Asia/Manila')

def apply_nine_pm_cutoff():
    """
    Enforce the cutoff for visits:

    - For *today* (after 9:00 PM PH time):
        Active (today)   -> Completed, end_time = 21:00 if missing/earlier
        Upcoming (today) -> Expired, start_time/end_time = 21:00 if missing

    - For *past days* (visit_date < today):
        Any remaining Active/Upcoming are also finalized the same way.
    """
    now_ph = django_now().astimezone(PHILIPPINES_TZ)
    today = now_ph.date()
    cutoff = dtime(21, 0)

    # ---- 1) Today, only if it's already past 9PM ----
    if now_ph.time() >= cutoff:
        today_qs = Visit.objects.filter(
            visit_date=today,
            status__in=["Active", "Upcoming"],
        )
    else:
        today_qs = Visit.objects.none()

    # ---- 2) Any past days with wrong statuses ----
    past_qs = Visit.objects.filter(
        visit_date__lt=today,
        status__in=["Active", "Upcoming"],
    )

    visits_to_fix = today_qs | past_qs

    for visit in visits_to_fix:
        if visit.status == "Active":
            # Finalize as completed at 9PM of that day
            if visit.end_time is None or visit.end_time < cutoff:
                visit.end_time = cutoff
            visit.status = "Completed"

        elif visit.status == "Upcoming":
            # No-show → expired; make sure times are not null
            if visit.start_time is None:
                visit.start_time = cutoff
            if visit.end_time is None:
                visit.end_time = cutoff
            visit.status = "Expired"

        visit.save(update_fields=["status", "start_time", "end_time"])

def _extract_identifier(actor_str):
    """
    Extract the identifier (username/email) from an actor string.

    Examples:
        "Lyra Nuevas (admin01)"      -> "admin01"
        "Juan Dela Cruz (staff01)"   -> "staff01"
        "visitor@email.com"         -> "visitor@email.com"
        "" or None                  -> ""
    """
    if not actor_str:
        return ""

    actor_str = str(actor_str).strip()

    # If it has parentheses, assume "Name (identifier)"
    if "(" in actor_str and ")" in actor_str:
        try:
            inside = actor_str.split("(", 1)[1].split(")", 1)[0]
            return inside.strip()
        except Exception:
            # Fallback to original
            return actor_str

    # Otherwise just return the whole thing (could be an email or username)
    return actor_str

# ========== Helper: Format timestamp to Philippine Time ==========
def format_ph_time(timestamp):
    if not timestamp:
        return "-"
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return "-"
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    ph_time = timestamp.astimezone(timezone(timedelta(hours=8)))
    return ph_time.strftime("%b %d, %Y")


def dashboard_view(request):
    """
    Visitor dashboard.

    - Requires logged-in visitor.
    - Auto-expires visits strictly BEFORE today (Upcoming/Active -> Expired).
    - DOES NOT recompute status for today/future — we trust
      whatever staff / other logic already stored in the DB.
    - Shows only Upcoming + Active visits in the "Recent Visit Codes" tickets,
      limited to the next 3 by date/time.
    """
    if "user_email" not in request.session:
        return redirect("login_app:login")

    user_email = request.session["user_email"]

    now_ph = django_now().astimezone(PHILIPPINES_TZ)
    today = now_ph.date()

    # 1) Auto-expire past visits (yesterday and earlier) that are still Upcoming/Active
    Visit.objects.filter(
        user_email=user_email,
        visit_date__lt=today,
        status__in=["Upcoming", "Active"],
    ).update(status="Expired")

    # 2) Load all visits for this user
    all_visits = Visit.objects.filter(user_email=user_email)

    completed_visits_count = all_visits.filter(status="Completed").count()

    for visit in all_visits:
        visit_date_obj = visit.visit_date
        visit.visit_date_obj = visit_date_obj

        # Friendly display date
        if visit_date_obj == today:
            visit.display_date = f"Today, {visit_date_obj.strftime('%b %d')}"
        else:
            visit.display_date = visit_date_obj.strftime("%b %d, %Y")

        # Display times (we're only formatting, not changing anything)
        if visit.start_time:
            visit.formatted_start_time = visit.start_time.strftime("%I:%M %p")
        else:
            visit.formatted_start_time = "Not checked in"

        if visit.end_time:
            visit.formatted_end_time = visit.end_time.strftime("%I:%M %p")
        else:
            visit.formatted_end_time = "Pending"

        # For sorting (if no start_time, push early in the day)
        visit.visit_start_datetime = datetime.combine(
            visit.visit_date,
            visit.start_time or datetime.min.time(),
        )

    # 3) Use the status exactly as stored in DB
    active_visits = [v for v in all_visits if v.status == "Active"]
    upcoming_visits = [v for v in all_visits if v.status == "Upcoming"]

    active_upcoming = active_visits + upcoming_visits
    active_upcoming.sort(key=lambda x: x.visit_start_datetime)

    # Only show the next 3 relevant passes on the dashboard
    display_visits = active_upcoming[:3]

    context = {
        "user_email": user_email,
        "user_first_name": request.session.get("user_first_name"),

        # Tickets section
        "visits": display_visits,

        # Stats cards
        "active_visits": active_visits,
        "upcoming_visits": upcoming_visits,
        "completed_visits_count": completed_visits_count,

        "notifications": [],
        "today": today,
    }

    return render(request, "dashboard_app/dashboard.html", context)


# ========== ADMIN DASHBOARD ==========
def admin_dashboard_view(request):
    if "admin_username" not in request.session:
        return redirect("login_app:login")

    current_admin = request.session["admin_username"]

    # Fetch current admin's superadmin status
    try:
        admin_obj = Administrator.objects.get(username=current_admin)
        is_superadmin = admin_obj.is_superadmin
        
        # SAVE TO SESSION SO OTHER PAGES CAN USE IT
        request.session['is_superadmin'] = is_superadmin 
        
    except Administrator.DoesNotExist:
        is_superadmin = False
        request.session['is_superadmin'] = False

    # === Totals ===
    admins_count = Administrator.objects.count()
    staff_count = FrontDeskStaff.objects.count()
    visitors_count = User.objects.count()

    # === Fetch Logs ===
    try:
        all_logs = list_logs(limit=50)
        # Convert to objects with display_time for template compatibility
        logs = []
        for log_data in all_logs:
            # Create a simple object-like structure
            class LogObj:
                def __init__(self, data):
                    self.action_type = data['action_type']
                    self.description = data['description']
                    self.actor = data['actor']
                    self.actor_role = data['actor_role']
                    self.display_time = format_ph_time(data['created_at'])
                    self.log_id = data.get('log_id')
            logs.append(LogObj(log_data))
    except Exception as e:
        print("Error fetching logs:", e)
        logs = []

    # === Format logs and filter for notifications ===
    notifications = []
    for log in logs:
        actor = log.actor or ""
        action_type = (log.action_type or "").strip()
        description = (log.description or "").lower()

        # Only show notifications from *other* admins
        if log.actor_role == "Admin" and current_admin not in actor:
            # Staff-related (create/edit/deactivate/password reset)
            if (
                action_type in ["Staff Management", "Security"]
                or any(keyword in description for keyword in ["staff", "password"])
            ):
                notifications.append({
                    "id": log.log_id,
                    "title": "Staff Update",
                    "message": f"{actor} {log.description}",
                    "time": log.display_time,
                })
            # Visitor-related (add/remove/edit)
            elif (
                action_type in ["Account", "Visitor Management"]
                or "visitor" in description
            ):
                notifications.append({
                    "id": log.log_id,
                    "title": "Visitor Update",
                    "message": f"{actor} {log.description}",
                    "time": log.display_time,
                })

    context = {
        "admin_username": request.session["admin_username"],
        "admin_first_name": request.session.get("admin_first_name"),
        "is_superadmin": is_superadmin,
        "total_admins": admins_count,
        "total_staff": staff_count,
        "total_visitors": visitors_count,
        "recent_activities": logs[:10],
        "notifications": notifications[:5],
    }

    return render(request, "dashboard_app/admin_dashboard.html", context)


# ========= NOTIFICATIONS API (for dropdown + AJAX) =========
def admin_notifications_api(request):
    if "admin_username" not in request.session:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    current_admin = request.session["admin_username"]

    try:
        # Use the same list_logs function as the initial page load for consistency
        all_logs = list_logs(limit=50)
        
        # Convert to dict format for easier processing
        logs_data = all_logs
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    notifications = []
    for log_data in logs_data:
        actor = log_data.get('actor') or ""
        action_type = (log_data.get('action_type') or "").strip()
        description = (log_data.get('description') or "").lower()
        log_id = log_data.get('log_id')
        actor_role = log_data.get('actor_role', "")

        # Only show notifications from *other* admins
        if actor_role == "Admin" and current_admin not in actor:
            # Staff-related (create/edit/deactivate/password reset)
            if (
                action_type in ["Staff Management", "Security"]
                or any(keyword in description for keyword in ["staff", "password"])
            ):
                notifications.append({
                    "id": log_id,
                    "title": "Staff Update",
                    "message": f"{actor} {log_data.get('description')}",
                    "time": log_data.get('created_at'),
                })
            # Visitor-related (add/remove/edit)
            elif (
                action_type in ["Account", "Visitor Management"]
                or "visitor" in description
            ):
                notifications.append({
                    "id": log_id,
                    "title": "Visitor Update",
                    "message": f"{actor} {log_data.get('description')}",
                    "time": log_data.get('created_at'),
                })

    return JsonResponse({"notifications": notifications[:5]})


def admin_recent_activities_api(request):
    if "admin_username" not in request.session:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        # Use the same list_logs function as the initial page load for consistency
        all_logs = list_logs(limit=50)
        
        # Format logs for JSON response - take first 10 to match dashboard view
        activities = []
        for log_data in all_logs[:10]:
            activities.append({
                'action_type': log_data.get('action_type'),
                'description': log_data.get('description'),
                'actor': log_data.get('actor'),
                'log_id': log_data.get('log_id')
            })

        return JsonResponse({"activities": activities})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ========== DELETE NOTIFICATIONS  ==========
@csrf_exempt
@require_POST
def delete_notification_api(request):
    if "admin_username" not in request.session:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        body = json.loads(request.body)
        notif_id = body.get("notif_id")
        admin = request.session["admin_username"]

        if not notif_id or not admin:
            return JsonResponse({"error": "Invalid notification or admin"}, status=400)

        # Create or update dismissed notification
        AdminDismissedNotification.objects.create(
            admin_username=admin,
            log_id=notif_id
        )

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ========== CLEAR ALL NOTIFICATIONS ==========
@csrf_exempt
@require_POST
def clear_notifications_api(request):
    if "admin_username" not in request.session:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        body = json.loads(request.body) if request.body else {}
        notif_ids = body.get("notif_ids")
        admin = request.session["admin_username"]

        if not notif_ids:
            # Get all undismissed notifications for this admin
            dismissed_ids = set(AdminDismissedNotification.objects.filter(
                admin_username=admin
            ).values_list('log_id', flat=True))
            
            all_log_ids = set(SystemLog.objects.all().values_list('log_id', flat=True))
            notif_ids = list(all_log_ids - dismissed_ids)

        # Create dismissed notifications for all undismissed logs
        for log_id in notif_ids:
            if log_id:
                AdminDismissedNotification.objects.get_or_create(
                    admin_username=admin,
                    log_id=log_id
                )

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ============================================================================
# ===== STAFF DASHBOARD - Enhanced with Code Checker & Check-in/Check-out ===
# ============================================================================

def staff_required(view_func):
    """Decorator to ensure only staff can access certain views"""
    def wrapper(request, *args, **kwargs):
        if 'staff_username' not in request.session:
            messages.warning(request, "Please log in as staff to access this page.")
            return redirect('login_app:login')
        return view_func(request, *args, **kwargs)
    return wrapper


@staff_required
def staff_dashboard_view(request):
    """Main staff dashboard with stats and quick code checker"""
    apply_nine_pm_cutoff()

    staff_username = request.session['staff_username']
    staff_first_name = request.session.get('staff_first_name', 'Staff')

    now_ph = django_now().astimezone(PHILIPPINES_TZ)
    today = now_ph.date()

    # 🔁 AUTO-COMPLETE / AUTO-EXPIRE AT 9:00 PM (PH TIME)
        # 🔁 AUTO-COMPLETE / AUTO-EXPIRE AT 9:00 PM (PH TIME)
    cutoff_time = dtime(21, 0)  # 9:00 PM

    if now_ph.time() >= cutoff_time:
        # 1) Auto-complete ACTIVE visits for today
        active_visits_to_complete = Visit.objects.filter(
            visit_date=today,
            status='Active',
        )
        for visit in active_visits_to_complete:
            # If no recorded end_time yet OR earlier than 9:00 PM, set it to 9:00 PM
            if visit.end_time is None or visit.end_time < cutoff_time:
                visit.end_time = cutoff_time
            visit.status = 'Completed'
            visit.save()

        # 2) Auto-expire UPCOMING visits for today (no-show)
        upcoming_visits_to_expire = Visit.objects.filter(
            visit_date=today,
            status='Upcoming',
        )
        for visit in upcoming_visits_to_expire:
            # Give them non-null "auto-closed" times at 9:00 PM
            if visit.start_time is None:
                visit.start_time = cutoff_time
            if visit.end_time is None:
                visit.end_time = cutoff_time
            visit.status = 'Expired'
            visit.save()

        logger.info(
            f"Auto-completed {active_visits_to_complete.count()} active visits "
            f"and auto-expired {upcoming_visits_to_expire.count()} upcoming visits "
            f"for {today} after cutoff {cutoff_time}."
        )


    try:
        # ✅ Use pk instead of id (always exists), and don't slice
        today_visits_qs = Visit.objects.filter(visit_date=today).order_by('start_time', 'pk')

        # ----- Update status for today's visits -----
        for visit in today_visits_qs:
            # ⛔ Skip visits that are already final (Completed or Expired)
            if visit.status in ['Completed', 'Expired']:
                continue

            if visit.start_time:
                visit_start = datetime.combine(
                    visit.visit_date,
                    visit.start_time
                ).replace(tzinfo=PHILIPPINES_TZ)

                if visit.end_time:
                    visit_end = datetime.combine(
                        visit.visit_date,
                        visit.end_time
                    ).replace(tzinfo=PHILIPPINES_TZ)
                else:
                    # If there is no end_time, treat it as until end of day
                    visit_end = datetime.combine(
                        visit.visit_date,
                        datetime.max.time()
                    ).replace(tzinfo=PHILIPPINES_TZ)

                if visit.end_time is None and visit.status == 'Active':
                    new_status = 'Active'
                elif visit_start <= now_ph <= visit_end:
                    new_status = 'Active'
                elif now_ph > visit_end:
                    new_status = 'Expired'
                else:
                    new_status = 'Upcoming'
            else:
                new_status = 'Upcoming'

            if visit.status != new_status:
                visit.status = new_status
                visit.save()

        # ----- Dashboard stats -----
        today_visits_count = today_visits_qs.count()
        active_visits_count = today_visits_qs.filter(status='Active').count()
        checked_in_count = today_visits_qs.filter(status__in=['Active', 'Completed']).count()

        # ===== 🔁 LIVE FEED – *only today's entries* =====
        recent_checkins = SystemLog.objects.filter(
            action_type__in=[
                "Visitor Check-In",
                "Visitor Check-Out",
                "Walk-In Registration",
            ],
            created_at__date=today,
        ).order_by("-created_at")[:15]

        for checkin in recent_checkins:
            try:
                checkin.display_time = checkin.created_at.astimezone(
                    PHILIPPINES_TZ
                ).strftime("%b %d, %Y %I:%M %p")
            except Exception:
                checkin.display_time = str(checkin.created_at)

        code_check_result = request.session.pop('code_check_result', None)

        context = {
            'staff_username': staff_username,
            'staff_first_name': staff_first_name,
            'today_date': today.strftime('%B %d, %Y'),
            'today_visits_count': today_visits_count,
            'active_visits_count': active_visits_count,
            'checked_in_count': checked_in_count,
            'today_visits': list(today_visits_qs),
            'recent_checkins': recent_checkins,
            'code_check_result': code_check_result,
        }

        return render(request, 'dashboard_app/staff_dashboard.html', context)

    except Exception as e:
        logger.error(f"Error loading staff dashboard: {str(e)}")
        messages.error(request, "An error occurred while loading the dashboard.")
        return render(request, 'dashboard_app/staff_dashboard.html', {
            'staff_username': staff_username,
            'staff_first_name': staff_first_name,
            'today_date': today.strftime('%B %d, %Y'),
            'today_visits_count': 0,
            'active_visits_count': 0,
            'checked_in_count': 0,
            'today_visits': [], 
            'recent_checkins': [],
        })

@staff_required
def code_checker(request):
    """Dedicated code checker page (if you ever navigate to it directly)"""
    staff_first_name = request.session.get('staff_first_name', 'Staff')

    # 🔹 One-time read: remove from session as soon as we use them
    code_check_result = request.session.pop('code_check_result', None)
    entered_code = request.session.pop('entered_code', None)

    context = {
        'staff_first_name': staff_first_name,
        'code_check_result': code_check_result,
        'entered_code': entered_code,   # may be None → template default will kick in
    }
    return render(request, 'dashboard_app/code_checker.html', context)

@staff_required
@require_POST
def check_code(request):
    """Check if a visit code is valid and push result into session"""
    visit_code = request.POST.get('visit_code', '').strip().upper()

    if not visit_code:
        messages.error(request, "Please enter a visit code.")
        return redirect('dashboard_app:code_checker')

    # 🔹 SAVE the entered code so the next GET can prefill it
    request.session['entered_code'] = visit_code

    try:
        try:
            visit = Visit.objects.get(code=visit_code)

                        # 🔁 --- AUTO-REFRESH STATUS (9PM + time window) ---
            now_ph = django_now().astimezone(PHILIPPINES_TZ)
            today = now_ph.date()
            cutoff_time = dtime(21, 0)  # 9:00 PM

            # Only apply special rules for today's visits
            if visit.visit_date == today:
                # 1) 9PM rule: Active -> Completed, Upcoming -> Expired
                if now_ph.time() >= cutoff_time:
                    if visit.status == "Active":
                        # Ensure a proper checkout time at 9:00 PM
                        if visit.end_time is None or visit.end_time < cutoff_time:
                            visit.end_time = cutoff_time
                        visit.status = "Completed"
                        visit.save()
                    elif visit.status == "Upcoming":
                        # No-show: give it non-null times at 9:00 PM
                        if visit.start_time is None:
                            visit.start_time = cutoff_time
                        if visit.end_time is None:
                            visit.end_time = cutoff_time
                        visit.status = "Expired"
                        visit.save()
                else:
                    # 2) Time-window logic like staff dashboard (before 9 PM)
                    if visit.start_time:
                        visit_start = datetime.combine(
                            visit.visit_date,
                            visit.start_time
                        ).replace(tzinfo=PHILIPPINES_TZ)

                        if visit.end_time:
                            visit_end = datetime.combine(
                                visit.visit_date,
                                visit.end_time
                            ).replace(tzinfo=PHILIPPINES_TZ)
                        else:
                            # No end_time yet → treat as until end of day
                            visit_end = datetime.combine(
                                visit.visit_date,
                                datetime.max.time()
                            ).replace(tzinfo=PHILIPPINES_TZ)

                        if visit_start <= now_ph <= visit_end:
                            new_status = "Active"
                        elif now_ph > visit_end:
                            new_status = "Expired"
                        else:
                            new_status = "Upcoming"
                    else:
                        new_status = "Upcoming"

                    if visit.status != new_status:
                        visit.status = new_status
                        visit.save()
            # 🔁 --- END AUTO-REFRESH ---

            # ✅ Always read the latest values from DB into session "memory"
            request.session['code_check_result'] = {
                'status': 'success',
                'message': 'Visit code found and verified!',
                'visit': {
                    'code': visit.code,
                    'user_email': visit.user_email,
                    'purpose': visit.purpose,
                    'department': visit.department,
                    'visit_date': visit.visit_date.isoformat() if visit.visit_date else None,
                    'status': visit.status,   # ← updated status
                    'start_time': visit.start_time.isoformat() if visit.start_time else None,
                    'end_time': visit.end_time.isoformat() if visit.end_time else None,
                }
            }
        except Visit.DoesNotExist:
            request.session['code_check_result'] = {
                'status': 'error',
                'message': f'Visit code "{visit_code}" not found in the system.'
            }

        # Redirect back to whichever page initiated the check (dashboard or code checker)
        referer = request.META.get('HTTP_REFERER', '')
        if 'staff_dashboard' in referer or ('staff' in referer and 'dashboard' in referer):
            return redirect('dashboard_app:staff_dashboard')
        else:
            return redirect('dashboard_app:code_checker')

    except Exception as e:
        logger.error(f"Error checking code: {str(e)}")
        messages.error(request, "An error occurred while checking the code.")
        return redirect('dashboard_app:code_checker')

@staff_required
@require_POST
def check_in_visitor(request):
    """Check in a visitor (staff side)"""
    visit_code = request.POST.get('visit_code', '').strip().upper()
    staff_username = request.session['staff_username']
    staff_first_name = request.session.get('staff_first_name', 'Staff')

    if not visit_code:
        messages.error(request, "Invalid visit code.")
        return redirect('dashboard_app:code_checker')

    try:
        try:
            visit = Visit.objects.get(code=visit_code)
        except Visit.DoesNotExist:
            messages.error(request, f'Visit code "{visit_code}" not found.')
            return redirect('dashboard_app:code_checker')

        if visit.status != 'Upcoming':
            messages.warning(request, f'Visit is already {visit.status}. Cannot check in.')
            return redirect('dashboard_app:code_checker')

        # 🔒 TIME-BASED RESTRICTION (PH time)
        current_dt = django_now().astimezone(PHILIPPINES_TZ)
        current_t = current_dt.time()

        # Allowed window: 7:30 AM <= time < 9:00 PM
        start_allowed = dtime(7, 30)   # 7:30 AM
        end_allowed = dtime(21, 0)     # 9:00 PM

        if not (start_allowed <= current_t < end_allowed):
            messages.error(
                request,
                "⏰ Check-in is only allowed from 7:30 AM to 9:00 PM. "
                "Please advise the visitor to return during operating hours."
            )
            return redirect('dashboard_app:code_checker')

        # ✅ Proceed with normal check-in
        checkin_time = current_dt.time()

        visit.status = "Active"
        visit.start_time = checkin_time
        visit.save()

        # Log entry
        SystemLog.objects.create(
            actor=f"{staff_first_name} ({staff_username})",
            action_type="Visitor Check-In",
            description=f"Checked in visitor with code {visit_code} for {visit.purpose} at {visit.department}",
            actor_role="Staff",
            created_at=current_dt,
        )

        messages.success(request, f'✅ Visitor checked in successfully! Code: {visit_code}')
        logger.info(f"Visitor checked in by {staff_username}: {visit_code}")

    except Exception as e:
        logger.error(f"Error checking in visitor: {str(e)}")
        messages.error(request, "An error occurred during check-in.")

    return redirect('dashboard_app:staff_dashboard')

@staff_required
@require_POST
def check_out_visitor(request):
    """Check out a visitor and record the actual check-out time"""
    visit_code = request.POST.get('visit_code', '').strip().upper()
    staff_username = request.session['staff_username']
    staff_first_name = request.session.get('staff_first_name', 'Staff')

    if not visit_code:
        messages.error(request, "Invalid visit code.")
        return redirect('dashboard_app:code_checker')

    try:
        try:
            visit = Visit.objects.get(code=visit_code)
        except Visit.DoesNotExist:
            messages.error(request, f'Visit code "{visit_code}" not found.')
            return redirect('dashboard_app:code_checker')

        if visit.status != 'Active':
            messages.warning(request, f'Visit is {visit.status}. Cannot check out.')
            return redirect('dashboard_app:code_checker')

        current_time = django_now().astimezone(PHILIPPINES_TZ)
        checkout_time = current_time.time()

        visit.status = "Completed"
        visit.end_time = checkout_time
        visit.save()

        formatted_time = current_time.strftime("%I:%M %p")

        SystemLog.objects.create(
            actor=f"{staff_first_name} ({staff_username})",
            action_type="Visitor Check-Out",
            description=f"Checked out visitor with code {visit_code} from {visit.department}",
            actor_role="Staff",
            created_at=current_time,
        )

        messages.success(
            request,
            f'✅ Visitor checked out successfully at {formatted_time}! Code: {visit_code}'
        )

        logger.info(f"Visitor checked out by {staff_username}: {visit_code} at {formatted_time}")

    except Exception as e:
        logger.error(f"Error checking out visitor: {str(e)}")
        messages.error(request, "An error occurred during check-out.")

    return redirect('dashboard_app:staff_dashboard')
