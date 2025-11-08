from django.shortcuts import render, redirect
from supabase import create_client
import os
from dotenv import load_dotenv
from django.contrib import messages
import re
from django.contrib.auth.hashers import make_password
from manage_reports_logs_app import services as logs_services

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Password strength checker
def is_strong_password(password):
    if len(password) < 8: return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"[a-z]", password): return False
    if not re.search(r"[0-9]", password): return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): return False
    return True

def register_view(request):
    if request.method == 'POST':
        # ===== Determine visitor type =====
        visitor_type_select = request.POST.get('visitorType', '').strip()
        visitor_type_other = request.POST.get('visitor_type_other', '').strip()
        visitor_type = visitor_type_other if visitor_type_select == "Other" else visitor_type_select

        # ===== Prepare form data =====
        first_name = request.POST.get('firstName', '').strip()
        last_name = request.POST.get('lastName', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirmPassword', '')

        # Data for template rendering on error
        data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "visitor_type_select": visitor_type_select,
            "visitor_type_other": visitor_type_other,
        }

        # ===== Validations =====
        if password != confirm_password:
            data["error"] = "Passwords do not match."
            return render(request, 'register_app/register.html', data)

        if not is_strong_password(password):
            data["error"] = "Password too weak. Must contain uppercase, lowercase, number, and special character."
            return render(request, 'register_app/register.html', data)

        if not re.fullmatch(r"09\d{9}", phone):
            data["error"] = "Invalid phone number. Must start with 09 and be 11 digits."
            data["phone"] = ''
            return render(request, 'register_app/register.html', data)

        # Check for duplicate email
        existing_email = supabase.table("users").select("*").ilike("email", email).execute()
        if existing_email.data:
            data["error"] = "Email already registered."
            data["email"] = ''
            return render(request, 'register_app/register.html', data)

        # Check for duplicate phone
        existing_phone = supabase.table("users").select("*").eq("phone", phone).execute()
        if existing_phone.data:
            data["error"] = "Phone number already registered."
            data["phone"] = ''
            return render(request, 'register_app/register.html', data)

        # ===== Insert new visitor =====
        insert_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "visitor_type": visitor_type,
            "password": make_password(password)
        }

        resp = supabase.table("users").insert(insert_data).execute()

        # Check insert success using resp.data
        if not resp.data:  # insert failed if data is empty or None
            data["error"] = "Registration failed. Please try again."
            return render(request, 'register_app/register.html', data)

        # ===== Log the registration =====
        actor = f"{first_name} {last_name} ({email})"
        logs_services.create_log(
            actor=actor,
            action_type="Visitor Registration",
            description="New visitor account created.",
            actor_role="Visitor"
        )

        messages.success(request, "Registration successful! Please login.")
        return redirect('login_app:login')

    # GET request
    return render(request, 'register_app/register.html')
