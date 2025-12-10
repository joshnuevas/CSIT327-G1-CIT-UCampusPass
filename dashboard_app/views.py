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
from .models import Visit, SystemLog, Notification, AdminDismissedNotification
from login_app.models import Administrator, FrontDeskStaff
from register_app.models import User

# Import logs service
from manage_reports_logs_app.services import list_logs

# Setup logging
logger = logging.getLogger(__name__)

# Philippines timezone
PHILIPPINES_TZ = pytz.timezone('Asia/Manila')

# ============================================================================
# ===== HELPER FUNCTIONS =====
# ============================================================================

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
            if visit.end_time is None or visit.end_time < cutoff:
                visit.end_time = cutoff
            visit.status = "Completed"

        elif visit.status == "Upcoming":
            if visit.start_time is None:
                visit.start_time = cutoff
            if visit.end_time is None:
                visit.end_time = cutoff
            visit.status = "Expired"

        visit.save(update_fields=["status", "start_time", "end_time"])

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
    ph_time = timestamp.astimezone(PHILIPPINES_TZ)
    return ph_time.strftime("%b %d, %Y %I:%M %p")

# ============================================================================
# ===== VISITOR DASHBOARD =====
# ============================================================================

def dashboard_view(request):
    """
    Visitor dashboard.
    """
    if "user_email" not in request.session:
        return redirect("login_app:login")

    user_email = request.session["user_email"]
    now_ph = django_now().astimezone(PHILIPPINES_TZ)
    today = now_ph.date()

    # 1) Auto-expire past visits
    Visit.objects.filter(
        user_email=user_email,
        visit_date__lt=today,
        status__in=["Upcoming", "Active"],
    ).update(status="Expired")

    # 2) Load all visits for this user
    # 2) Load all visits for this user
    all_visits = Visit.objects.filter(user_email=user_email)

    # Lifetime completed visits
    completed_visits_count = all_visits.filter(status="Completed").count()

    # 🔢 Visits This Month (any status for this month)
    first_day_of_month = today.replace(day=1)
    # trick to get first day of next month
    if first_day_of_month.month == 12:
        first_day_next_month = first_day_of_month.replace(year=first_day_of_month.year + 1, month=1)
    else:
        first_day_next_month = first_day_of_month.replace(month=first_day_of_month.month + 1)

    month_visits_count = all_visits.filter(
        visit_date__gte=first_day_of_month,
        visit_date__lt=first_day_next_month,
    ).count()

    for visit in all_visits:
        visit_date_obj = visit.visit_date
        visit.visit_date_obj = visit_date_obj

        if visit_date_obj == today:
            visit.display_date = f"Today, {visit_date_obj.strftime('%b %d')}"
        else:
            visit.display_date = visit_date_obj.strftime("%b %d, %Y")

        if visit.start_time:
            visit.formatted_start_time = visit.start_time.strftime("%I:%M %p")
        else:
            visit.formatted_start_time = "Not checked in"

        if visit.end_time:
            visit.formatted_end_time = visit.end_time.strftime("%I:%M %p")
        else:
            visit.formatted_end_time = "Pending"

        visit.visit_start_datetime = datetime.combine(
            visit.visit_date,
            visit.start_time or datetime.min.time(),
        )

    # 3) Sort and Filter
    active_visits = [v for v in all_visits if v.status == "Active"]
    upcoming_visits = [v for v in all_visits if v.status == "Upcoming"]

    active_upcoming = active_visits + upcoming_visits
    active_upcoming.sort(key=lambda x: x.visit_start_datetime)
    display_visits = active_upcoming[:3]

    # 4) Fetch User Notifications (Real DB - for initial load)
    user_notifications = []
    try:
        current_user_obj = User.objects.filter(email=user_email).first()
        if current_user_obj:
            notifs_qs = Notification.objects.filter(
                receiver_user=current_user_obj
            ).order_by('-created_at')[:5]
            
            for n in notifs_qs:
                user_notifications.append({
                    "id": n.notification_id,
                    "title": n.title,
                    "message": n.message,
                    "type": n.type,
                    "time": format_ph_time(n.created_at)
                })
    except Exception as e:
        logger.error(f"Error fetching user notifications: {e}")

    context = {
        "user_email": user_email,
        "user_first_name": request.session.get("user_first_name"),
        "user_last_name": request.session.get("user_last_name"),  # 👈 add this
        "visits": display_visits,
        "active_visits": active_visits,
        "upcoming_visits": upcoming_visits,
        "completed_visits_count": completed_visits_count,
        "month_visits_count": month_visits_count,
        "notifications": user_notifications,
        "today": today,
    }

    return render(request, "dashboard_app/dashboard.html", context)


# ============================================================================
# ===== ADMIN DASHBOARD =====
# ============================================================================

def admin_dashboard_view(request):
    if "admin_username" not in request.session:
        return redirect("login_app:login")

    current_admin = request.session["admin_username"]
    admin_obj = None

    try:
        admin_obj = Administrator.objects.get(username=current_admin)
        is_superadmin = admin_obj.is_superadmin
        request.session['is_superadmin'] = is_superadmin
    except Administrator.DoesNotExist:
        is_superadmin = False
        request.session['is_superadmin'] = False

    # === Totals ===
    admins_count = Administrator.objects.count()
    staff_count = FrontDeskStaff.objects.count()
    visitors_count = User.objects.count()

    # === Fetch Logs ===
    recent_activities = []
    try:
        all_logs = list_logs(limit=10) 
        for log_data in all_logs:
            class LogObj:
                def __init__(self, data):
                    self.action_type = data.get('action_type', '')
                    self.description = data.get('description', '')
                    self.actor = data.get('actor', '')
                    self.actor_role = data.get('actor_role', '')
                    self.display_time = format_ph_time(data.get('created_at'))
                    self.log_id = data.get('log_id')
            recent_activities.append(LogObj(log_data))
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")

    # === Fetch Real Notifications ===
    notifications = []
    if admin_obj:
        try:
            notifs_qs = Notification.objects.filter(
                receiver_admin=admin_obj
            ).order_by('-created_at')[:5]

            for n in notifs_qs:
                notifications.append({
                    "id": n.notification_id,
                    "title": n.title,
                    "message": n.message,
                    "type": n.type,
                    "time": format_ph_time(n.created_at),
                })
        except Exception as e:
            logger.error(f"Error fetching admin notifications: {e}")

    context = {
        "admin_username": request.session["admin_username"],
        "admin_first_name": request.session.get("admin_first_name"),
        "is_superadmin": is_superadmin,
        "total_admins": admins_count,
        "total_staff": staff_count,
        "total_visitors": visitors_count,
        "recent_activities": recent_activities,
        "notifications": notifications,
    }

    return render(request, "dashboard_app/admin_dashboard.html", context)


# ============================================================================
# ===== ADMIN APIs =====
# ============================================================================

def admin_recent_activities_api(request):
    """API for the JS polling to get recent logs"""
    if "admin_username" not in request.session:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        all_logs = list_logs(limit=10)
        activities = []
        for log in all_logs:
            activities.append({
                "action_type": log.get('action_type'),
                "description": log.get('description'),
                "actor": log.get('actor'),
                "time": format_ph_time(log.get('created_at')) 
            })
        return JsonResponse({"activities": activities})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def create_notification(receiver_admin=None, receiver_user=None, title="", message="", type="system_alert", visit=None):
    """Helper to create a notification in the DB."""
    try:
        Notification.objects.create(
            receiver_admin=receiver_admin,
            receiver_user=receiver_user,
            title=title,
            message=message,
            type=type,
            visit=visit
        )
    except Exception as e:
        logger.error(f"Failed to create notification: {str(e)}")

def admin_notifications_api(request):
    """API to fetch notifications dynamically."""
    if "admin_username" not in request.session:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    current_admin_username = request.session["admin_username"]
    try:
        admin_obj = Administrator.objects.get(username=current_admin_username)
        notifications_qs = Notification.objects.filter(
            receiver_admin=admin_obj
        ).order_by('-created_at')[:20]

        notifications_data = []
        for n in notifications_qs:
            notifications_data.append({
                "id": n.notification_id,
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "time": format_ph_time(n.created_at),
                "is_read": n.is_read 
            })

        return JsonResponse({"notifications": notifications_data})
    except Administrator.DoesNotExist:
        return JsonResponse({"notifications": []})

@csrf_exempt
@require_POST
def delete_notification_api(request):
    """
    Permanently deletes a single notification (Admin).
    """
    if "admin_username" not in request.session:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        body = json.loads(request.body)
        notif_id = body.get("notif_id")

        if not notif_id:
            return JsonResponse({"error": "Missing notification ID"}, status=400)

        current_admin = Administrator.objects.get(username=request.session["admin_username"])
        
        notif = Notification.objects.get(notification_id=notif_id, receiver_admin=current_admin)
        notif.delete() 

        return JsonResponse({"success": True})
    except Notification.DoesNotExist:
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
@csrf_exempt
@require_POST
def clear_notifications_api(request):
    """
    Permanently deletes ALL notifications for the current admin.
    """
    if "admin_username" not in request.session:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        admin_obj = Administrator.objects.get(username=request.session["admin_username"])
        Notification.objects.filter(receiver_admin=admin_obj).delete()
        return JsonResponse({"success": True})
    except Administrator.DoesNotExist:
        return JsonResponse({"error": "Admin not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ============================================================================
# ===== VISITOR APIs (NEW) =====
# ============================================================================

def visitor_notifications_api(request):
    """API to fetch visitor notifications"""
    if "user_email" not in request.session:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        user = User.objects.get(email=request.session["user_email"])
        qs = Notification.objects.filter(receiver_user=user).order_by('-created_at')[:20]
        
        data = [{
            "id": n.notification_id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "time": format_ph_time(n.created_at),
            "is_read": n.is_read
        } for n in qs]
        
        return JsonResponse({"notifications": data})
    except User.DoesNotExist:
        return JsonResponse({"notifications": []})

@csrf_exempt
@require_POST
def delete_visitor_notification_api(request):
    """Visitor Delete Single"""
    if "user_email" not in request.session:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        body = json.loads(request.body)
        user = User.objects.get(email=request.session["user_email"])
        Notification.objects.filter(
            notification_id=body.get("notif_id"), 
            receiver_user=user
        ).delete()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_POST
def clear_visitor_notifications_api(request):
    """Visitor Clear All"""
    if "user_email" not in request.session:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        user = User.objects.get(email=request.session["user_email"])
        Notification.objects.filter(receiver_user=user).delete()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ============================================================================
# ===== STAFF DASHBOARD =====
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

    # 🔁 AUTO-COMPLETE / AUTO-EXPIRE AT 9:00 PM
    cutoff_time = dtime(21, 0)

    if now_ph.time() >= cutoff_time:
        active_visits_to_complete = Visit.objects.filter(
            visit_date=today,
            status='Active',
        )
        for visit in active_visits_to_complete:
            if visit.end_time is None or visit.end_time < cutoff_time:
                visit.end_time = cutoff_time
            visit.status = 'Completed'
            visit.save()

        upcoming_visits_to_expire = Visit.objects.filter(
            visit_date=today,
            status='Upcoming',
        )
        for visit in upcoming_visits_to_expire:
            if visit.start_time is None:
                visit.start_time = cutoff_time
            if visit.end_time is None:
                visit.end_time = cutoff_time
            visit.status = 'Expired'
            visit.save()

    try:
        today_visits_qs = Visit.objects.filter(visit_date=today).order_by('start_time', 'pk')

        for visit in today_visits_qs:
            if visit.status in ['Completed', 'Expired']:
                continue

            if visit.start_time:
                visit_start = datetime.combine(visit.visit_date, visit.start_time).replace(tzinfo=PHILIPPINES_TZ)

                if visit.end_time:
                    visit_end = datetime.combine(visit.visit_date, visit.end_time).replace(tzinfo=PHILIPPINES_TZ)
                else:
                    visit_end = datetime.combine(visit.visit_date, datetime.max.time()).replace(tzinfo=PHILIPPINES_TZ)

                # ================= BUG FIX APPLIED HERE =================
                # If a visit is ALREADY Active, do NOT revert it to Upcoming,
                # even if current time is before start_time (manual early check-in).
                if visit.status == 'Active':
                    if now_ph > visit_end:
                        new_status = 'Expired'
                    else:
                        new_status = 'Active' # Sticky status
                # Only check time window if it is NOT yet Active
                elif visit_start <= now_ph <= visit_end:
                    new_status = 'Active'
                elif now_ph > visit_end:
                    new_status = 'Expired'
                else:
                    new_status = 'Upcoming'
                # ========================================================

            else:
                new_status = 'Upcoming'

            if visit.status != new_status:
                visit.status = new_status
                visit.save()

        today_visits_count = today_visits_qs.count()
        active_visits_count = today_visits_qs.filter(status='Active').count()
        checked_in_count = today_visits_qs.filter(status__in=['Active', 'Completed']).count()

        recent_checkins = SystemLog.objects.filter(
            action_type__in=["Visitor Check-In", "Visitor Check-Out", "Walk-In Registration"],
            created_at__date=today,
        ).order_by("-created_at")[:15]

        for checkin in recent_checkins:
            try:
                checkin.display_time = checkin.created_at.astimezone(PHILIPPINES_TZ).strftime("%b %d, %Y %I:%M %p")
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
            'today_date': today.strftime('%B %d, %Y'),
            'today_visits_count': 0,
            'active_visits_count': 0,
            'checked_in_count': 0,
            'today_visits': [], 
            'recent_checkins': [],
        })

@staff_required
def code_checker(request):
    staff_first_name = request.session.get('staff_first_name', 'Staff')
    code_check_result = request.session.pop('code_check_result', None)
    entered_code = request.session.pop('entered_code', None)
    context = {
        'staff_first_name': staff_first_name,
        'code_check_result': code_check_result,
        'entered_code': entered_code,
    }
    return render(request, 'dashboard_app/code_checker.html', context)

@staff_required
@require_POST
def check_code(request):
    visit_code = request.POST.get('visit_code', '').strip().upper()
    if not visit_code:
        messages.error(request, "Please enter a visit code.")
        return redirect('dashboard_app:code_checker')

    request.session['entered_code'] = visit_code

    try:
        try:
            visit = Visit.objects.get(code=visit_code)
            now_ph = django_now().astimezone(PHILIPPINES_TZ)
            today = now_ph.date()
            cutoff_time = dtime(21, 0)

            # 🔒 HARD RULE: only allow staff to check codes for TODAY
            if visit.visit_date != today:
                scheduled_str = visit.visit_date.strftime("%b %d, %Y") if visit.visit_date else "an unknown date"
                request.session['code_check_result'] = {
                    "status": "error",
                    "message": (
                        f'Visit code "{visit_code}" is scheduled for {scheduled_str}, '
                        f'not today. Staff can only process visit codes for today\'s date.'
                    ),
                }
            else:
                # ✅ Only for TODAY: apply your status logic
                if now_ph.time() >= cutoff_time:
                    if visit.status == "Active":
                        if visit.end_time is None or visit.end_time < cutoff_time:
                            visit.end_time = cutoff_time
                        visit.status = "Completed"
                        visit.save()
                    elif visit.status == "Upcoming":
                        if visit.start_time is None:
                            visit.start_time = cutoff_time
                        if visit.end_time is None:
                            visit.end_time = cutoff_time
                        visit.status = "Expired"
                        visit.save()
                else:
                    if visit.start_time:
                        visit_start = datetime.combine(
                            visit.visit_date, visit.start_time
                        ).replace(tzinfo=PHILIPPINES_TZ)

                        if visit.end_time:
                            visit_end = datetime.combine(
                                visit.visit_date, visit.end_time
                            ).replace(tzinfo=PHILIPPINES_TZ)
                        else:
                            visit_end = datetime.combine(
                                visit.visit_date, datetime.max.time()
                            ).replace(tzinfo=PHILIPPINES_TZ)

                        # Sticky Active status
                        if visit.status == "Active":
                            if now_ph > visit_end:
                                new_status = "Expired"
                            else:
                                new_status = "Active"
                        elif visit_start <= now_ph <= visit_end:
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

                # Build SUCCESS result only if date is today
                if visit.visit_date == today:
                    request.session['code_check_result'] = {
                        'status': 'success',
                        'message': 'Visit code found and verified!',
                        'visit': {
                            'code': visit.code,
                            'user_email': visit.user_email,
                            'purpose': visit.purpose,
                            'department': visit.department,
                            'visit_date': visit.visit_date.isoformat() if visit.visit_date else None,
                            'status': visit.status,
                            'start_time': visit.start_time.isoformat() if visit.start_time else None,
                            'end_time': visit.end_time.isoformat() if visit.end_time else None,
                        }
                    }

        except Visit.DoesNotExist:
            request.session['code_check_result'] = {
                'status': 'error',
                'message': f'Visit code "{visit_code}" not found in the system.'
            }

        # Same redirect logic as before
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
    """Check in a visitor"""
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

        current_dt = django_now().astimezone(PHILIPPINES_TZ)
        current_t = current_dt.time()
        start_allowed = dtime(7, 30)
        end_allowed = dtime(21, 0)

        if not (start_allowed <= current_t < end_allowed):
            messages.error(request, "⏰ Check-in is only allowed from 7:30 AM to 9:00 PM.")
            return redirect('dashboard_app:code_checker')

        visit.status = "Active"
        visit.start_time = current_dt.time()
        visit.save()

        # Log
        SystemLog.objects.create(
            actor=f"{staff_first_name} ({staff_username})",
            action_type="Visitor Check-In",
            description=f"Checked in visitor with code {visit_code} for {visit.purpose} at {visit.department}",
            actor_role="Staff",
            created_at=current_dt,
        )

        # ✅ NOTIFY VISITOR
        try:
            visitor_user = User.objects.filter(email=visit.user_email).first()
            if visitor_user:
                create_notification(
                    receiver_user=visitor_user,
                    title="Visit Check-In",
                    message=f"You have been checked in for your visit to {visit.department}.",
                    type="visit_update",
                    visit=visit
                )
        except Exception as e:
            logger.error(f"Failed to send visitor check-in notification: {e}")

        messages.success(request, f'✅ Visitor checked in successfully! Code: {visit_code}')
        logger.info(f"Visitor checked in by {staff_username}: {visit_code}")

    except Exception as e:
        logger.error(f"Error checking in visitor: {str(e)}")
        messages.error(request, "An error occurred during check-in.")

    return redirect('dashboard_app:staff_dashboard')

@staff_required
@require_POST
def check_out_visitor(request):
    """Check out a visitor"""
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

        # Log
        SystemLog.objects.create(
            actor=f"{staff_first_name} ({staff_username})",
            action_type="Visitor Check-Out",
            description=f"Checked out visitor with code {visit_code} from {visit.department}",
            actor_role="Staff",
            created_at=current_time,
        )

        # ✅ NOTIFY VISITOR
        try:
            visitor_user = User.objects.filter(email=visit.user_email).first()
            if visitor_user:
                create_notification(
                    receiver_user=visitor_user,
                    title="Visit Check-Out",
                    message=f"You have been checked out from {visit.department}. Thank you for visiting!",
                    type="visit_update",
                    visit=visit
                )
        except Exception as e:
            logger.error(f"Failed to send visitor check-out notification: {e}")

        messages.success(request, f'✅ Visitor checked out successfully at {formatted_time}! Code: {visit_code}')
        logger.info(f"Visitor checked out by {staff_username}: {visit_code} at {formatted_time}")

    except Exception as e:
        logger.error(f"Error checking out visitor: {str(e)}")
        messages.error(request, "An error occurred during check-out.")

    return redirect('dashboard_app:staff_dashboard')