from django.shortcuts import render, redirect
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def history_view(request):
    # Redirect if not logged in
    if 'user_email' not in request.session:
        return redirect('login_app:login')

    user_email = request.session['user_email']
    visits_resp = supabase.table("visits").select("*").eq("user_email", user_email).execute()
    visits = visits_resp.data

    # Format visit dates and times like in dashboard
    from datetime import datetime, date
    today = date.today()
    for visit in visits:
        visit_date_obj = datetime.strptime(visit['visit_date'], "%Y-%m-%d").date()
        visit['display_date'] = f"Today, {visit_date_obj.strftime('%b %d')}" if visit_date_obj == today else visit_date_obj.strftime("%b %d, %Y")
        visit['formatted_start_time'] = datetime.strptime(visit['start_time'], "%H:%M:%S").strftime("%I:%M %p")
        visit['formatted_end_time'] = datetime.strptime(visit['end_time'], "%H:%M:%S").strftime("%I:%M %p")

    context = {
        "user_email": user_email,
        "user_first_name": request.session.get('user_first_name'),
        "visits": visits,
    }
    return render(request, 'history_app/history.html', context)
