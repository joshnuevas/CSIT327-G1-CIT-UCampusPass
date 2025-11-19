# dashboard_app/views.py
from django.shortcuts import render, redirect
import os, json
from dotenv import load_dotenv
from datetime import datetime, date, timezone, timedelta
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

# Setup logging
logger = logging.getLogger(__name__)

# Philippines timezone
PHILIPPINES_TZ = pytz.timezone('Asia/Manila')

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
    return ph_time.strftime("%b %d, %Y %I:%M %p")

def dashboard_view(request):
    if 'user_email' not in request.session:
        return redirect('login_app:login')

    user_email = request.session['user_email']
    
    # Use Django ORM instead of Supabase
    all_visits = Visit.objects.filter(user_email=user_email)
    now = datetime.now()    
    today = date.today()
    
    # COUNT COMPLETED VISITS instead of expired ones
    completed_visits_count = all_visits.filter(status='Completed').count()

    for visit in all_visits:
        visit_date_obj = visit.visit_date
        visit.visit_date_obj = visit_date_obj

        if visit_date_obj == today:
            visit.display_date = f"Today, {visit_date_obj.strftime('%b %d')}"
        else:
            visit.display_date = visit_date_obj.strftime("%b %d, %Y")

        # Format start time - handle null start_time for unchecked-in visits
        if visit.start_time:
            visit.formatted_start_time = visit.start_time.strftime("%I:%M %p")
        else:
            visit.formatted_start_time = "Not checked in"

        # Format end time ONLY if it exists (not None)
        if visit.end_time:
            visit.formatted_end_time = visit.end_time.strftime("%I:%M %p")
        else:
            visit.formatted_end_time = "Pending"

        # Handle start_time parsing - for booked visits not yet checked in, start_time is None
        if visit.start_time:
            visit_start = datetime.combine(visit.visit_date, visit.start_time)
            visit.visit_start_datetime = visit_start

            # Handle None end_time for status checking
            if visit.end_time:
                visit_end = datetime.combine(visit.visit_date, visit.end_time)
            else:
                # If no end time, use end of day for status check purposes
                visit_end = datetime.combine(visit.visit_date, datetime.max.time())

            # FIXED STATUS LOGIC: Preserve Completed status
            if visit.status == 'Completed':
                # If already completed, keep it as completed - DON'T change to Expired!
                new_status = 'Completed'
            elif visit.end_time is None and visit.status == 'Active':
                # Keep as Active (visitor is currently on-site)
                new_status = 'Active'
            elif visit_start <= now <= visit_end:
                new_status = 'Active'
            elif now > visit_end:
                new_status = 'Expired'
            else:
                new_status = 'Upcoming'
        else:
            # For visits not yet checked in, set a placeholder datetime and keep as Upcoming
            visit.visit_start_datetime = datetime.combine(visit.visit_date, datetime.min.time())
            new_status = 'Upcoming'

        # Only update status if it actually changed AND it's not already Completed
        if visit.status != new_status and visit.status != 'Completed':
            visit.status = new_status
            # Update using Django ORM
            Visit.objects.filter(code=visit.code).update(status=new_status)

    active_upcoming = [v for v in all_visits if v.status in ['Active', 'Upcoming']]
    active_upcoming.sort(key=lambda x: x.visit_start_datetime)
    display_visits = active_upcoming[:3]

    context = {
        "user_email": user_email,
        "user_first_name": request.session.get('user_first_name'),
        "visits": display_visits,
        "active_visits": [v for v in all_visits if v.status == 'Active'],
        "upcoming_visits": [v for v in all_visits if v.status == 'Upcoming'],
        "completed_visits_count": completed_visits_count,
        "notifications": [],
        "today": today,
    }

    return render(request, 'dashboard_app/dashboard.html', context)

# ========== ADMIN DASHBOARD ==========
def admin_dashboard_view(request):
    if "admin_username" not in request.session:
        return redirect("login_app:login")

    # === Totals ===
    admins_count = Administrator.objects.count()
    staff_count = FrontDeskStaff.objects.count()
    visitors_count = User.objects.count()

    # === Fetch Logs ===
    try:
        logs = SystemLog.objects.all().order_by('-created_at')[:50]
    except Exception as e:
        print("Error fetching logs:", e)
        logs = []

    current_admin = request.session["admin_username"]

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
                    "time": format_ph_time(log.created_at),
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
                    "time": format_ph_time(log.created_at),
                })

    context = {
        "admin_username": request.session["admin_username"],
        "admin_first_name": request.session.get("admin_first_name"),
        "total_admins": admins_count,
        "total_staff": staff_count,
        "total_visitors": visitors_count,
        "recent_activities": logs[:5],
        "notifications": notifications[:5],
    }

    return render(request, "dashboard_app/admin_dashboard.html", context)

# ========= NOTIFICATIONS API (for dropdown + AJAX) =========
def admin_notifications_api(request):
    if "admin_username" not in request.session:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    current_admin = request.session["admin_username"]

    try:
        # fetch logs
        logs = SystemLog.objects.all().order_by('-created_at')[:50]

        # fetch dismissed log_ids for this admin
        dismissed_ids = set(AdminDismissedNotification.objects.filter(
            admin_username=current_admin
        ).values_list('log_id', flat=True))

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    notifications = []
    for log in logs:
        log_id = log.log_id
        if log_id in dismissed_ids:
            continue  # skip logs this admin already dismissed

        actor = log.actor or ""
        action_type = (log.action_type or "").strip()
        description = (log.description or "").lower()

        if log.actor_role == "Admin" and current_admin not in actor:
            if (
                action_type in ["Staff Management", "Security"]
                or any(keyword in description for keyword in ["staff", "password"])
            ):
                notifications.append({
                    "id": log_id,
                    "title": "Staff Update",
                    "message": f"{actor} {log.description}",
                    "time": log.created_at.isoformat(),
                })
            elif (
                action_type in ["Account", "Visitor Management"]
                or "visitor" in description
            ):
                notifications.append({
                    "id": log_id,
                    "title": "Visitor Update",
                    "message": f"{actor} {log.description}",
                    "time": log.created_at.isoformat(),
                })

    return JsonResponse({"notifications": notifications[:10]})

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
    staff_username = request.session['staff_username']
    staff_first_name = request.session.get('staff_first_name', 'Staff')
    
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    
    try:
        # Get today's visits using Django ORM
        today_visits = Visit.objects.filter(visit_date=today_str)
        
        # Update status for today's visits if needed
        now = datetime.now()
        for visit in today_visits:
            # ✅ Do not touch completed visits
            if visit.status == 'Completed':
                continue

            if visit.start_time:
                visit_start = datetime.combine(visit.visit_date, visit.start_time)
                visit_end = datetime.combine(
                    visit.visit_date, datetime.max.time()
                ) if not visit.end_time else datetime.combine(visit.visit_date, visit.end_time)

                if visit.end_time is None and visit.status == 'Active':
                    new_status = 'Active'
                elif visit_start <= now <= visit_end:
                    new_status = 'Active'
                elif now > visit_end:
                    new_status = 'Expired'
                else:
                    new_status = 'Upcoming'
            else:
                new_status = 'Upcoming'

            if visit.status != new_status:
                visit.status = new_status
                visit.save()

        # Count stats
        today_visits_count = today_visits.count()
        active_visits_count = today_visits.filter(status='Active').count()
        checked_in_count = today_visits.filter(status__in=['Active', 'Completed']).count()
        
        # Get recent check-ins from logs
        recent_checkins = SystemLog.objects.filter(
            action_type__in=['Visitor Check-In', 'Visitor Check-Out']
        ).order_by('-created_at')[:5]
        
        # Format timestamps
        for checkin in recent_checkins:
            try:
                checkin.display_time = checkin.created_at.astimezone(PHILIPPINES_TZ).strftime('%b %d, %Y %I:%M %p')
            except:
                checkin.display_time = str(checkin.created_at)
        
        # Handle code check result if present
        code_check_result = None
        if 'code_check_result' in request.session:
            code_check_result = request.session.pop('code_check_result')
        
        context = {
            'staff_username': staff_username,
            'staff_first_name': staff_first_name,
            'today_date': today.strftime('%B %d, %Y'),
            'today_visits_count': today_visits_count,
            'active_visits_count': active_visits_count,
            'checked_in_count': checked_in_count,
            'today_visits': list(today_visits[:10]),  # Show first 10
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
    """Dedicated code checker page"""
    staff_first_name = request.session.get('staff_first_name', 'Staff')
    
    # Handle code check result if present
    code_check_result = None
    if 'code_check_result' in request.session:
        code_check_result = request.session.pop('code_check_result')
    
    context = {
        'staff_first_name': staff_first_name,
        'code_check_result': code_check_result,
    }
    
    return render(request, 'dashboard_app/code_checker.html', context)

@staff_required
@require_POST
def check_code(request):
    """Check if a visit code is valid"""
    visit_code = request.POST.get('visit_code', '').strip().upper()
    
    if not visit_code:
        messages.error(request, "Please enter a visit code.")
        return redirect('dashboard_app:code_checker')
    
    try:
        # Query the visits table using Django ORM
        try:
            visit = Visit.objects.get(code=visit_code)
            # Code found - Convert date objects to strings for session storage
            request.session['code_check_result'] = {
                'status': 'success',
                'message': 'Visit code found and verified!',
                'visit': {
                    'code': visit.code,
                    'purpose': visit.purpose,
                    'department': visit.department,
                    'visit_date': visit.visit_date.isoformat() if visit.visit_date else None,  # Convert to string
                    'status': visit.status,
                    'start_time': visit.start_time.isoformat() if visit.start_time else None,  # Convert to string
                    'end_time': visit.end_time.isoformat() if visit.end_time else None,  # Convert to string
                }
            }
        except Visit.DoesNotExist:
            # Code not found
            request.session['code_check_result'] = {
                'status': 'error',
                'message': f'Visit code "{visit_code}" not found in the system.'
            }
        
        # Redirect to referrer or code checker
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
        # Get visit details using Django ORM
        try:
            visit = Visit.objects.get(code=visit_code)
        except Visit.DoesNotExist:
            messages.error(request, f'Visit code "{visit_code}" not found.')
            return redirect('dashboard_app:code_checker')
        
        # Check if visit can be checked in
        if visit.status != 'Upcoming':
            messages.warning(request, f'Visit is already {visit.status}. Cannot check in.')
            return redirect('dashboard_app:code_checker')
        
        # Get current time in Philippines timezone
        current_time = datetime.now(PHILIPPINES_TZ)
        checkin_time = current_time.time()

        # Update visit status to Active and set start_time
        visit.status = "Active"
        visit.start_time = checkin_time
        visit.save()
        
        # Create log entry
        log_entry = SystemLog(
            actor=f"{staff_first_name} ({staff_username})",
            action_type="Visitor Check-In",
            description=f"Checked in visitor with code {visit_code} for {visit.purpose} at {visit.department}",
            actor_role="Staff",
            created_at=current_time
        )
        log_entry.save()
        
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
        # Get visit details using Django ORM
        try:
            visit = Visit.objects.get(code=visit_code)
        except Visit.DoesNotExist:
            messages.error(request, f'Visit code "{visit_code}" not found.')
            return redirect('dashboard_app:code_checker')
        
        # Check if visit can be checked out
        if visit.status != 'Active':
            messages.warning(request, f'Visit is {visit.status}. Cannot check out.')
            return redirect('dashboard_app:code_checker')
        
        # Get current time in Philippines timezone
        current_time = datetime.now(PHILIPPINES_TZ)
        checkout_time = current_time.time()
        
        # Update visit status to Completed and set end_time
        visit.status = "Completed"
        visit.end_time = checkout_time
        visit.save()
        
        # Create log entry
        log_entry = SystemLog(
            actor=f"{staff_first_name} ({staff_username})",
            action_type="Visitor Check-Out",
            description=f"Checked out visitor with code {visit_code} from {visit.department} at {checkout_time}",
            actor_role="Staff",
            created_at=current_time
        )
        log_entry.save()
        
        messages.success(request, f'✅ Visitor checked out successfully at {current_time.strftime("%I:%M %p")}! Code: {visit_code}')
        logger.info(f"Visitor checked out by {staff_username}: {visit_code} at {checkout_time}")
        
    except Exception as e:
        logger.error(f"Error checking out visitor: {str(e)}")
        messages.error(request, "An error occurred during check-out.")
    
    return redirect('dashboard_app:staff_dashboard')