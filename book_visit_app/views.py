from django.shortcuts import render, redirect
from supabase import create_client
import os
from dotenv import load_dotenv
from django.contrib import messages
import random
import string
from django.core.mail import send_mail

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_visit_code(purpose):
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"CIT-{purpose[:3].upper()}-{random_str}"

# ---------------- Book Visit ----------------
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

        user_resp = supabase.table("users").select("user_id", "first_name").eq("email", user_email).execute()
        user = user_resp.data[0]
        user_id = user['user_id']
        first_name = user['first_name']

        # Insert visit record
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

        # ---------------- Email Notification ----------------
        subject = "CIT-U CampusPass | Visit Confirmation"
        message = (
            f"Hi {first_name},\n\n"
            f"Your visit has been successfully booked!\n\n"
            f"📅 Date: {visit_date}\n"
            f"🕒 Time: {start_time} - {end_time}\n"
            f"🏢 Department: {department}\n"
            f"🎯 Purpose: {purpose}\n"
            f"🔑 Visit Code: {code}\n\n"
            f"Please present this visit code upon arrival.\n"
            f"Thank you for using CIT-U CampusPass!"
        )

        try:
            send_mail(
                subject,
                message,
                'your_email@gmail.com',  # same as DEFAULT_FROM_EMAIL
                [user_email],
                fail_silently=False,
            )
            messages.success(request, f"Visit booked! A confirmation email has been sent to {user_email}.")
        except Exception as e:
            print(f"Email error: {e}")
            messages.warning(request, "Visit booked, but failed to send confirmation email.")

        return redirect('dashboard')

    return render(request, 'book_visit_app/book_visit.html')
