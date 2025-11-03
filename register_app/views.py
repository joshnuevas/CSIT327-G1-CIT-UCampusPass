from django.shortcuts import render, redirect
from supabase import create_client
import os
from dotenv import load_dotenv
from django.contrib import messages
import re
from django.contrib.auth.hashers import make_password

# Supabase
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def is_strong_password(password):
    if len(password) < 8: return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"[a-z]", password): return False
    if not re.search(r"[0-9]", password): return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): return False
    return True

def register_view(request):
    if request.method == 'POST':
        visitor_type_select = request.POST.get('visitorType', '').strip()
        visitor_type_other = request.POST.get('visitor_type_other', '').strip()
        if visitor_type_select == "Other":
            visitor_type = visitor_type_other
        else:
            visitor_type = visitor_type_select

        data = {
            "first_name": request.POST.get('firstName', '').strip(),
            "last_name": request.POST.get('lastName', '').strip(),
            "email": request.POST.get('email', '').strip().lower(),
            "phone": request.POST.get('phone', '').strip(),
            "visitor_type": visitor_type,
        }
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirmPassword', '')

        # Add to data for template rendering on error
        data["visitor_type_select"] = visitor_type_select
        data["visitor_type_other"] = visitor_type_other

        if password != confirm_password:
            data["error"] = "Passwords do not match."
            return render(request, 'register_app/register.html', data)

        if not is_strong_password(password):
            data["error"] = "Password too weak."
            return render(request, 'register_app/register.html', data)

        if not re.fullmatch(r"09\d{9}", data["phone"]):
            data["error"] = "Invalid phone number."
            data["phone"] = ''
            return render(request, 'register_app/register.html', data)

        if supabase.table("users").select("*").ilike("email", data["email"]).execute().data:
            data["error"] = "Email already registered."
            data["email"] = ''
            return render(request, 'register_app/register.html', data)

        if supabase.table("users").select("*").eq("phone", data["phone"]).execute().data:
            data["error"] = "Phone number already registered."
            data["phone"] = ''
            return render(request, 'register_app/register.html', data)

        supabase.table("users").insert({
            **data,
            "password": make_password(password)
        }).execute()

        messages.success(request, "Registration successful! Please login.")
        return redirect('login_app:login')

    return render(request, 'register_app/register.html')
