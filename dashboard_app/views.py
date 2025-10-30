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
        return redirect('login')

    user_email = request.session['user_email']
    visits_resp = supabase.table("visits").select("*").eq("user_email", user_email).execute()
    visits = visits_resp.data

    now = datetime.now()
    today = date.today()
    total_visits_count = 0

    for visit in visits:
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

    context = {
        "user_email": user_email,
        "user_first_name": request.session.get('user_first_name'),
        "visits": visits,
        "active_visits": [v for v in visits if v['status'] == 'Active'],
        "upcoming_visits": [v for v in visits if v['status'] == 'Upcoming'],
        "total_visits": total_visits_count,
        "notifications": [],
        "today": today,
    }

    return render(request, 'dashboard_app/dashboard.html', context)
