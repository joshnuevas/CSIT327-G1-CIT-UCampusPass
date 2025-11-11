from django.shortcuts import render, redirect
from supabase import create_client
import os, json
from dotenv import load_dotenv
from datetime import datetime, date, timezone, timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now as django_now

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


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

        visit['formatted_start_time'] = datetime.strptime(visit['start_time'], "%H:%M:%S").strftime("%I:%M %p")
        visit['formatted_end_time'] = datetime.strptime(visit['end_time'], "%H:%M:%S").strftime("%I:%M %p")

        visit_start = datetime.strptime(f"{visit['visit_date']} {visit['start_time']}", "%Y-%m-%d %H:%M:%S")
        visit_end = datetime.strptime(f"{visit['visit_date']} {visit['end_time']}", "%Y-%m-%d %H:%M:%S")
        visit['visit_start_datetime'] = visit_start

        if visit_start <= now <= visit_end:
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

# ========== STAFF DASHBOARD ==========
def staff_dashboard_view(request):
    if "staff_username" not in request.session:
        return redirect("login_app:login")

    context = {
        "staff_username": request.session["staff_username"],
        "staff_first_name": request.session.get("staff_first_name"),
    }
    return render(request, "dashboard_app/staff_dashboard.html", context)