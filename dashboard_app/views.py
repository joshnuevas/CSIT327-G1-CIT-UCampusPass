from django.shortcuts import render, redirect
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime, date

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


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

def admin_dashboard_view(request):
    if 'admin_username' not in request.session:
        return redirect('login_app:login')

    # ✅ Get total counts from Supabase
    total_admins = supabase.table("administrator").select("admin_id").execute()
    total_staff = supabase.table("front_desk_staff").select("staff_id").execute()
    total_visitors = supabase.table("users").select("user_id").execute()

    # ✅ Handle empty data safely
    admins_count = len(total_admins.data) if total_admins.data else 0
    staff_count = len(total_staff.data) if total_staff.data else 0
    visitors_count = len(total_visitors.data) if total_visitors.data else 0

    # ✅ Placeholder messages (for now)
    recent_activities = []
    notifications = []

    context = {
        "admin_username": request.session['admin_username'],
        "admin_first_name": request.session.get('admin_first_name'),
        "total_admins": admins_count,
        "total_staff": staff_count,
        "total_visitors": visitors_count,
        "recent_activities": recent_activities,
        "notifications": notifications,
    }

    return render(request, 'dashboard_app/admin_dashboard.html', context)


def staff_dashboard_view(request):
    if 'staff_username' not in request.session:
        return redirect('login_app:login')

    context = {
        "staff_username": request.session['staff_username'],
        "staff_first_name": request.session.get('staff_first_name'),
    }

    return render(request, 'dashboard_app/staff_dashboard.html', context)
