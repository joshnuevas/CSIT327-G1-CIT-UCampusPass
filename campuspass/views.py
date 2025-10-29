from django.shortcuts import render, redirect
from supabase import create_client
import os
from dotenv import load_dotenv
from django.contrib import messages
import random
import string
from datetime import datetime, date
import re  # Added for password validation
from django.contrib.auth.hashers import check_password

# ---------------- Supabase Setup ----------------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------- Password Strength Checker ----------------
def is_strong_password(password):
    """
    Check if a password meets the strength requirements:
    - At least 8 characters
    - Contains uppercase, lowercase, number, and special character
    """
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True


# ---------------- Register ----------------
from django.contrib.auth.hashers import make_password

def register_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('firstName', '').strip()
        last_name = request.POST.get('lastName', '').strip()
        email = request.POST.get('email', '').strip().lower()  # normalize email
        phone = request.POST.get('phone', '').strip()
        visitor_type = request.POST.get('visitorType') or request.POST.get('visitor_type_other', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirmPassword', '')

        # 1️⃣ Passwords must match
        if password != confirm_password:
            return render(request, 'campuspass/register.html', {"error": "Passwords do not match."})

        # 2️⃣ Check password strength
        if not is_strong_password(password):
            return render(request, 'campuspass/register.html', {
                "error": "Password too weak. Must be at least 8 characters and include uppercase, lowercase, number, and special symbol."
            })

        # 3️⃣ Validate Philippine phone number format
        if not re.fullmatch(r"09\d{9}$", phone):
            return render(request, 'campuspass/register.html', {
                "error": "Invalid phone number. It must start with '09' and be 11 digits long (e.g. 09123456789)."
            })

        # 4️⃣ Check if email already exists (case-insensitive)
        existing_email = supabase.table("users").select("*").ilike("email", email).execute()
        if existing_email.data and len(existing_email.data) > 0:
            return render(request, 'campuspass/register.html', {"error": "Email already registered."})

        # 5️⃣ Check if phone number already exists
        existing_phone = supabase.table("users").select("*").eq("phone", phone).execute()
        if existing_phone.data and len(existing_phone.data) > 0:
            return render(request, 'campuspass/register.html', {"error": "Phone number already registered."})

        # 6️⃣ Hash the password before storing
        hashed_password = make_password(password)

        # 7️⃣ Insert user into database
        supabase.table("users").insert({
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "visitor_type": visitor_type,
            "password": hashed_password
        }).execute()

        # 8️⃣ Success message and redirect
        messages.success(request, "Registration successful! Please login.")
        return redirect('login')

    # GET request: render registration form
    return render(request, 'campuspass/register.html')

# ---------------- Login ----------------
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email').strip().lower()
        password = request.POST.get('password', '')

        # Fetch the user by email
        user_resp = supabase.table("users").select("*").eq("email", email).execute()
        if user_resp.data and len(user_resp.data) > 0:
            user = user_resp.data[0]

            # Check the password
            if check_password(password, user['password']):
                request.session['user_email'] = email
                request.session['user_first_name'] = user.get('first_name')

                messages.add_message(request, messages.SUCCESS, "Login successful!", extra_tags='login-success')
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid email or password.")
        else:
            messages.error(request, "Invalid email or password.")

        return redirect('login')

    return render(request, 'campuspass/login.html')



# ---------------- Dashboard ----------------
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

    return render(request, 'campuspass/dashboard.html', context)


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

        # Handle "Other" inputs (visitor_type removed)
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

    return render(request, 'campuspass/book_visit.html')


# ---------------- Logout ----------------
def logout_view(request):
    request.session.flush()
    return redirect('login')
