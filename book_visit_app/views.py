from django.shortcuts import render, redirect
from supabase import create_client
import os
from dotenv import load_dotenv
from django.contrib import messages
import random
import string

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_visit_code(purpose):
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"CIT-{purpose[:3].upper()}-{random_str}"

def book_visit_view(request):
    if 'user_email' not in request.session:
        return redirect('login')

    if request.method == 'POST':
        user_email = request.session['user_email']
        purpose = request.POST.get('purpose_other') or request.POST.get('purpose')
        department = request.POST.get('department_other') or request.POST.get('department')
        visit_date = request.POST.get('visit_date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')

        code = generate_visit_code(purpose)
        user_resp = supabase.table("users").select("user_id").eq("email", user_email).execute()
        user_id = user_resp.data[0]['user_id']

        supabase.table("visits").insert({
            "user_id": user_id,
            "user_email": user_email,
            "code": code,
            "purpose": purpose,
            "department": department,
            "visit_date": visit_date,
            "start_time": start_time,
            "end_time": end_time,
            "status": "Upcoming"
        }).execute()

        messages.success(request, f"Visit booked! Your code: {code}")
        return redirect('dashboard')

    return render(request, 'book_visit_app/book_visit.html')
