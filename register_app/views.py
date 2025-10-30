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
        first_name = request.POST.get('firstName', '').strip()
        last_name = request.POST.get('lastName', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        visitor_type = request.POST.get('visitorType') or request.POST.get('visitor_type_other', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirmPassword', '')

        if password != confirm_password:
            return render(request, 'user_register/register.html', {"error": "Passwords do not match."})
        if not is_strong_password(password):
            return render(request, 'user_register/register.html', {"error": "Password too weak."})
        if not re.fullmatch(r"09\d{9}$", phone):
            return render(request, 'user_register/register.html', {"error": "Invalid phone number."})

        if supabase.table("users").select("*").ilike("email", email).execute().data:
            return render(request, 'user_register/register.html', {"error": "Email already registered."})
        if supabase.table("users").select("*").eq("phone", phone).execute().data:
            return render(request, 'user_register/register.html', {"error": "Phone number already registered."})

        supabase.table("users").insert({
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "visitor_type": visitor_type,
            "password": make_password(password)
        }).execute()

        messages.success(request, "Registration successful! Please login.")
        return redirect('login')

    return render(request, 'register_app/register.html')
