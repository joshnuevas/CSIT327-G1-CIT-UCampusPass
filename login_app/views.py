from django.shortcuts import render, redirect
from supabase import create_client
import os
from dotenv import load_dotenv
from django.contrib import messages
from django.contrib.auth.hashers import check_password

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email').strip().lower()
        password = request.POST.get('password', '')

        user_resp = supabase.table("users").select("*").eq("email", email).execute()
        if user_resp.data and len(user_resp.data) > 0:
            user = user_resp.data[0]
            if check_password(password, user['password']):
                request.session['user_email'] = email
                request.session['user_first_name'] = user.get('first_name')
                messages.success(request, "Login successful!")
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid email or password.")
        else:
            messages.error(request, "Invalid email or password.")

        return redirect('login')

    return render(request, 'login_app/login.html')

def logout_view(request): 
    request.session.flush() 
    return redirect('login')
