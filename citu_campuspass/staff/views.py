from django.shortcuts import render, redirect
from supabase import create_client
import os
from dotenv import load_dotenv
from django.contrib import messages

# ---------------- Supabase Setup ----------------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create your views here.

def register(request):
    return render(request, 'staff/staff_register.html')

def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Assuming staff table exists in Supabase, similar to users
        staff_resp = supabase.table("staff").select("*").eq("username", username).eq("password", password).execute()
        if staff_resp.data:
            request.session['staff_username'] = username
            request.session['staff_first_name'] = staff_resp.data[0].get('first_name')

            # Add tag so modal shows
            messages.add_message(request, messages.SUCCESS, "Login successful!", extra_tags='login-success')

            return redirect('staff:staff_dashboard')
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('staff:staff_login')

    return render(request, 'staff/staff_login.html')
