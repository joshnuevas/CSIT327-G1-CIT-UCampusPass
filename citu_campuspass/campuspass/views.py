from django.shortcuts import render, redirect
from supabase import create_client
import os
from dotenv import load_dotenv
from django.contrib import messages
import random
import string
from datetime import datetime, date

# ---------------- Supabase Setup ----------------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- Register ----------------
def register_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('firstName')
        last_name = request.POST.get('lastName')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirmPassword')

        if password != confirm_password:
            return render(request, 'register.html', {"error": "Passwords do not match."})

        existing = supabase.table("users").select("*").eq("email", email).execute()
        if existing.data:
            return render(request, 'register.html', {"error": "Email already registered."})

        supabase.table("users").insert({
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "password": password
        }).execute()

        messages.success(request, "Registration successful! Please login.")
        return redirect('login')

    return render(request, 'register.html')


# ---------------- Login ----------------
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user_resp = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if user_resp.data:
            request.session['user_email'] = email
            request.session['user_first_name'] = user_resp.data[0].get('first_name')

            # Add tag so modal shows
            messages.add_message(request, messages.SUCCESS, "Login successful!", extra_tags='login-success')

            return redirect('dashboard')
        else:
            messages.error(request, "Invalid email or password.")
            return redirect('login')

    return render(request, 'login.html')

# ---------------- Dashboard ----------------
from django.shortcuts import render, redirect
from supabase import create_client
import os
from dotenv import load_dotenv
from django.contrib import messages
import random
import string
from datetime import datetime, date

# ---------------- Supabase Setup ----------------
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
    total_visits_count = 0  # only count expired visits

    for visit in visits:
        # Convert visit_date string to date object
        visit_date_obj = datetime.strptime(visit['visit_date'], "%Y-%m-%d").date()
        visit['visit_date_obj'] = visit_date_obj

        # Create display date
        if visit_date_obj == today:
            visit['display_date'] = f"Today, {visit_date_obj.strftime('%b %d')}"
        else:
            visit['display_date'] = visit_date_obj.strftime("%b %d, %Y")

        # Format times (12-hour AM/PM without seconds)
        visit['formatted_start_time'] = datetime.strptime(visit['start_time'], "%H:%M:%S").strftime("%I:%M %p")
        visit['formatted_end_time'] = datetime.strptime(visit['end_time'], "%H:%M:%S").strftime("%I:%M %p")

        # Determine status
        visit_start = datetime.strptime(f"{visit['visit_date']} {visit['start_time']}", "%Y-%m-%d %H:%M:%S")
        visit_end = datetime.strptime(f"{visit['visit_date']} {visit['end_time']}", "%Y-%m-%d %H:%M:%S")

        if visit_start <= now <= visit_end:
            new_status = 'Active'
        elif now > visit_end:
            new_status = 'Expired'
        else:
            new_status = 'Upcoming'

        # Update visit status if changed
        if visit['status'] != new_status:
            visit['status'] = new_status
            supabase.table("visits").update({"status": new_status}).eq("code", visit['code']).execute()

        # Count total visits (only expired)
        if new_status == 'Expired':
            total_visits_count += 1

    context = {
        "user_email": user_email,
        "user_first_name": request.session.get('user_first_name'),
        "visits": visits,
        "active_visits": [v for v in visits if v['status'] == 'Active'],
        "upcoming_visits": [v for v in visits if v['status'] == 'Upcoming'],
        "total_visits": total_visits_count,
        "notifications": [],  # you can replace with actual notifications
        "today": today,
    }

    return render(request, 'dashboard.html', context)

# ---------------- Generate Unique Visit Code ----------------
def generate_visit_code(purpose):
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"CIT-{purpose[:3].upper()}-{random_str}"


# ---------------- Book Visit ----------------
def book_visit_view(request):
    if 'user_email' not in request.session:
        return redirect('login')

    if request.method == 'POST':
        user_email = request.session['user_email']

        # Handle "Other" inputs
        purpose = request.POST.get('purpose_other') or request.POST.get('purpose')
        visitor_type = request.POST.get('visitor_type_other') or request.POST.get('visitor_type')
        department = request.POST.get('department_other') or request.POST.get('department')
        visit_date = request.POST.get('visit_date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')

        code = generate_visit_code(purpose)

        # Get user_id using the email stored in session
        user_resp = supabase.table("users").select("user_id").eq("email", user_email).execute()
        user_id = user_resp.data[0]['user_id']

        # ✅ Insert both user_id (FK) and user_email (for display/reference)
        supabase.table("visits").insert({
            "user_id": user_id,
            "user_email": user_email,  # keep this to know who made the visit
            "code": code,
            "purpose": purpose,
            "visitor_type": visitor_type,
            "department": department,
            "visit_date": visit_date,
            "start_time": start_time,
            "end_time": end_time,
            "status": "Upcoming"
        }).execute()

        messages.success(request, f"Visit booked! Your code: {code}")
        return redirect('dashboard')

    return render(request, 'book_visit.html')

# ---------------- Logout ----------------
def logout_view(request):
    request.session.flush()
    return redirect('login')
