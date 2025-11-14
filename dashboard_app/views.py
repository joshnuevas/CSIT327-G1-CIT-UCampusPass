from django.shortcuts import render, redirect
from supabase import create_client
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
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
import random
import string

# Setup logging
logger = logging.getLogger(__name__)

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    visits_resp = supabase.table("visits").select("*").eq("user_email", user_email).execute()
    all_visits = visits_resp.data

    now = datetime.now()    
    today = date.today()
    total_visits_count = 0

    for visit in all_visits:
        visit_date_obj = datetime.strptime(visit['visit_date'], "%Y-%m-%d").date()
        visit['visit_date_obj'] = visit_date_obj

        if visit_date_obj == today:
            visit['display_date'] = f"Today, {visit_date_obj.strftime('%b %d')}"
        else:
            visit['display_date'] = visit_date_obj.strftime("%b %d, %Y")

        # Format start time
        visit['formatted_start_time'] = datetime.strptime(visit['start_time'], "%H:%M:%S").strftime("%I:%M %p")
        
        # Format end time ONLY if it exists (not None)
        if visit['end_time']:
            visit['formatted_end_time'] = datetime.strptime(visit['end_time'], "%H:%M:%S").strftime("%I:%M %p")
        else:
            visit['formatted_end_time'] = "Pending"

        visit_start = datetime.strptime(f"{visit['visit_date']} {visit['start_time']}", "%Y-%m-%d %H:%M:%S")
        
        # Handle None end_time for status checking
        if visit['end_time']:
            visit_end = datetime.strptime(f"{visit['visit_date']} {visit['end_time']}", "%Y-%m-%d %H:%M:%S")
        else:
            # If no end time, use end of day for status check purposes
            visit_end = datetime.strptime(f"{visit['visit_date']} 23:59:59", "%Y-%m-%d %H:%M:%S")
        
        visit['visit_start_datetime'] = visit_start

        # Status logic - preserve Active status for checked-in visits without end_time
        if visit['end_time'] is None and visit['status'] == 'Active':
            # Keep as Active (visitor is currently on-site)
            new_status = 'Active'
        elif visit_start <= now <= visit_end:
            new_status = 'Active'
        elif now > visit_end:
            new_status = 'Expired'
        else:
            new_status = 'Upcoming'

        if visit['status'] != new_status:
            visit['status'] = new_status
            supabase.table("visits").update({"status": new_status}).eq("code", visit['code']).execute()

        if new_status == 'Expired':
            total_visits_count += 1

    active_upcoming = [v for v in all_visits if v['status'] in ['Active', 'Upcoming']]
    active_upcoming.sort(key=lambda x: x['visit_start_datetime'])
    display_visits = active_upcoming[:3]

    context = {
        "user_email": user_email,
        "user_first_name": request.session.get('user_first_name'),
        "visits": display_visits,
        "active_visits": [v for v in all_visits if v['status'] == 'Active'],
        "upcoming_visits": [v for v in all_visits if v['status'] == 'Upcoming'],
        "total_visits": total_visits_count,
        "notifications": [],
        "today": today,
    }

    return render(request, 'dashboard_app/dashboard.html', context)

# ========== ADMIN DASHBOARD ==========
def admin_dashboard_view(request):
    if "admin_username" not in request.session:
        return redirect("login_app:login")

    # === Totals ===
    total_admins = supabase.table("administrator").select("admin_id").execute()
    total_staff = supabase.table("front_desk_staff").select("staff_id").execute()
    total_visitors = supabase.table("users").select("user_id").execute()

    admins_count = len(total_admins.data or [])
    staff_count = len(total_staff.data or [])
    visitors_count = len(total_visitors.data or [])

    # === Fetch Logs ===
    try:
        logs_resp = (
            supabase.table("system_logs")
            .select("*")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        logs = logs_resp.data or []
    except Exception as e:
        print("Error fetching logs:", e)
        logs = []

    current_admin = request.session["admin_username"]

    # === Format logs and filter for notifications ===
    notifications = []
    for log in logs:
        actor = log.get("actor", "")
        action_type = (log.get("action_type") or "").strip()
        description = (log.get("description") or "").lower()

        # Only show notifications from *other* admins
        if log.get("actor_role") == "Admin" and current_admin not in actor:
            # Staff-related (create/edit/deactivate/password reset)
            if (
                action_type in ["Staff Management", "Security"]
                or any(keyword in description for keyword in ["staff", "password"])
            ):
                notifications.append({
                    "id": log.get("log_id"),
                    "title": "Staff Update",
                    "message": f"{actor} {log.get('description', '')}",
                    "time": format_ph_time(log.get("created_at")),
                })
            # Visitor-related (add/remove/edit)
            elif (
                action_type in ["Account", "Visitor Management"]
                or "visitor" in description
            ):
                notifications.append({
                    "id": log.get("log_id"),
                    "title": "Visitor Update",
                    "message": f"{actor} {log.get('description', '')}",
                    "time": format_ph_time(log.get("created_at")),
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
        logs_resp = (
            supabase.table("system_logs")
            .select("*")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        logs = logs_resp.data or []

        # fetch dismissed log_ids for this admin
        dismissed_resp = (
            supabase.table("admin_dismissed_notifications")
            .select("log_id")
            .eq("admin_username", current_admin)
            .execute()
        )
        dismissed_rows = dismissed_resp.data or []
        dismissed_ids = {r["log_id"] for r in dismissed_rows}

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    notifications = []
    for log in logs:
        log_id = log.get("log_id")
        if log_id in dismissed_ids:
            continue  # skip logs this admin already dismissed

        actor = log.get("actor", "")
        action_type = (log.get("action_type") or "").strip()
        description = (log.get("description") or "").lower()

        if log.get("actor_role") == "Admin" and current_admin not in actor:
            if (
                action_type in ["Staff Management", "Security"]
                or any(keyword in description for keyword in ["staff", "password"])
            ):
                notifications.append({
                    "id": log_id,
                    "title": "Staff Update",
                    "message": f"{actor} {log.get('description', '')}",
                    "time": log.get("created_at"),
                })
            elif (
                action_type in ["Account", "Visitor Management"]
                or "visitor" in description
            ):
                notifications.append({
                    "id": log_id,
                    "title": "Visitor Update",
                    "message": f"{actor} {log.get('description', '')}",
                    "time": log.get("created_at"),
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

        supabase.table("admin_dismissed_notifications").upsert(
            {"admin_username": admin, "log_id": notif_id},
            on_conflict="admin_username,log_id"
        ).execute()


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
            # fetch all undismissed notifications for this admin
            dismissed_resp = supabase.table("admin_dismissed_notifications") \
                                     .select("log_id") \
                                     .eq("admin_username", admin) \
                                     .execute()
            dismissed_ids = {r["log_id"] for r in (dismissed_resp.data or [])}

            logs_resp = supabase.table("system_logs") \
                                .select("log_id") \
                                .execute()
            all_log_ids = {r["log_id"] for r in (logs_resp.data or [])}

            notif_ids = list(all_log_ids - dismissed_ids)

        rows = [{"admin_username": admin, "log_id": nid} for nid in notif_ids if nid]
        if rows:
            supabase.table("admin_dismissed_notifications").upsert(
                rows,
                on_conflict="admin_username,log_id"
            ).execute()


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
            from django.contrib import messages
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
        # Get today's visits
        today_visits_resp = supabase.table("visits").select("*").eq("visit_date", today_str).execute()
        today_visits = today_visits_resp.data
        
        # Count stats
        today_visits_count = len(today_visits)
        active_visits_count = len([v for v in today_visits if v.get('status') == 'Active'])
        checked_in_count = len([v for v in today_visits if v.get('status') in ['Active', 'Completed']])
        
        # Get recent check-ins from logs
        recent_checkins_resp = supabase.table("system_logs").select("*").or_(
            "action_type.eq.Visitor Check-In,action_type.eq.Visitor Check-Out"
        ).order("created_at", desc=True).limit(5).execute()
        
        recent_checkins = recent_checkins_resp.data
        
        # Format timestamps
        for checkin in recent_checkins:
            try:
                created_at = datetime.fromisoformat(checkin['created_at'].replace('Z', '+00:00'))
                checkin['display_time'] = created_at.astimezone(PHILIPPINES_TZ).strftime('%b %d, %Y %I:%M %p')
            except:
                checkin['display_time'] = checkin.get('created_at', 'N/A')
        
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
            'today_visits': today_visits[:10],  # Show first 10
            'recent_checkins': recent_checkins,
            'code_check_result': code_check_result,
        }
        
        return render(request, 'dashboard_app/staff_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error loading staff dashboard: {str(e)}")
        from django.contrib import messages
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
        from django.contrib import messages
        messages.error(request, "Please enter a visit code.")
        return redirect('dashboard_app:code_checker')
    
    try:
        # Query the visits table
        visit_resp = supabase.table("visits").select("*").eq("code", visit_code).execute()
        
        if not visit_resp.data:
            # Code not found
            request.session['code_check_result'] = {
                'status': 'error',
                'message': f'Visit code "{visit_code}" not found in the system.'
            }
        else:
            # Code found
            visit = visit_resp.data[0]
            request.session['code_check_result'] = {
                'status': 'success',
                'message': 'Visit code found and verified!',
                'visit': visit
            }
        
        # Redirect to referrer or code checker
        referer = request.META.get('HTTP_REFERER', '')
        if 'staff_dashboard' in referer or ('staff' in referer and 'dashboard' in referer):
            return redirect('dashboard_app:staff_dashboard')
        else:
            return redirect('dashboard_app:code_checker')
            
    except Exception as e:
        logger.error(f"Error checking code: {str(e)}")
        from django.contrib import messages
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
        from django.contrib import messages
        messages.error(request, "Invalid visit code.")
        return redirect('dashboard_app:code_checker')
    
    try:
        # Get visit details
        visit_resp = supabase.table("visits").select("*").eq("code", visit_code).execute()
        
        if not visit_resp.data:
            from django.contrib import messages
            messages.error(request, f'Visit code "{visit_code}" not found.')
            return redirect('dashboard_app:code_checker')
        
        visit = visit_resp.data[0]
        
        # Check if visit can be checked in
        if visit['status'] != 'Upcoming':
            from django.contrib import messages
            messages.warning(request, f'Visit is already {visit["status"]}. Cannot check in.')
            return redirect('dashboard_app:code_checker')
        
        # Update visit status to Active
        supabase.table("visits").update({
            "status": "Active"
        }).eq("visit_id", visit['visit_id']).execute()
        
        # Create log entry
        current_time = datetime.now(PHILIPPINES_TZ)
        log_entry = {
            "actor": f"{staff_first_name} ({staff_username})",
            "action_type": "Visitor Check-In",
            "description": f"Checked in visitor with code {visit_code} for {visit['purpose']} at {visit['department']}",
            "actor_role": "Staff",
            "created_at": current_time.isoformat()
        }
        supabase.table("system_logs").insert(log_entry).execute()
        
        from django.contrib import messages
        messages.success(request, f'✅ Visitor checked in successfully! Code: {visit_code}')
        logger.info(f"Visitor checked in by {staff_username}: {visit_code}")
        
    except Exception as e:
        logger.error(f"Error checking in visitor: {str(e)}")
        from django.contrib import messages
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
        from django.contrib import messages
        messages.error(request, "Invalid visit code.")
        return redirect('dashboard_app:code_checker')
    
    try:
        # Get visit details
        visit_resp = supabase.table("visits").select("*").eq("code", visit_code).execute()
        
        if not visit_resp.data:
            from django.contrib import messages
            messages.error(request, f'Visit code "{visit_code}" not found.')
            return redirect('dashboard_app:code_checker')
        
        visit = visit_resp.data[0]
        
        # Check if visit can be checked out
        if visit['status'] != 'Active':
            from django.contrib import messages
            messages.warning(request, f'Visit is {visit["status"]}. Cannot check out.')
            return redirect('dashboard_app:code_checker')
        
        # Get current time in Philippines timezone
        current_time = datetime.now(PHILIPPINES_TZ)
        checkout_time = current_time.strftime('%H:%M:%S')
        
        # Update visit status to Completed and set end_time
        supabase.table("visits").update({
            "status": "Completed",
            "end_time": checkout_time  # Record actual checkout time
        }).eq("visit_id", visit['visit_id']).execute()
        
        # Create log entry
        log_entry = {
            "actor": f"{staff_first_name} ({staff_username})",
            "action_type": "Visitor Check-Out",
            "description": f"Checked out visitor with code {visit_code} from {visit['department']} at {checkout_time}",
            "actor_role": "Staff",
            "created_at": current_time.isoformat()
        }
        supabase.table("system_logs").insert(log_entry).execute()
        
        from django.contrib import messages
        messages.success(request, f'✅ Visitor checked out successfully at {current_time.strftime("%I:%M %p")}! Code: {visit_code}')
        logger.info(f"Visitor checked out by {staff_username}: {visit_code} at {checkout_time}")
        
    except Exception as e:
        logger.error(f"Error checking out visitor: {str(e)}")
        from django.contrib import messages
        messages.error(request, "An error occurred during check-out.")
    
    return redirect('dashboard_app:staff_dashboard')