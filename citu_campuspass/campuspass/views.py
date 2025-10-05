from django.shortcuts import render, redirect
from supabase import create_client
import os
from dotenv import load_dotenv
from django.contrib import messages

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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

        return redirect('login')

    return render(request, 'register.html')


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if user.data:
            request.session['user_email'] = email
            request.session['user_first_name'] = user.data[0].get('first_name')
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid email or password.")  # <-- use messages
            return redirect('login')

    return render(request, 'login.html')


def dashboard_view(request):
    if 'user_email' not in request.session:
        return redirect('login')

    context = {
        "user_email": request.session.get('user_email'),
        "user_first_name": request.session.get('user_first_name'),  # <-- this
        "visits": [],
        "active_visits": [],
        "upcoming_visits": [],
        "notifications": [],
    }
    return render(request, 'dashboard.html', context)


def logout_view(request):
    request.session.flush()
    return redirect('login')