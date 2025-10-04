from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import datetime

User = get_user_model()

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None

        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid email or password")

    return render(request, "login.html")


def register_view(request):
    if request.method == "POST":
        first_name = request.POST.get("firstName")
        last_name = request.POST.get("lastName")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirmPassword")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("register")

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        messages.success(request, "Account created successfully! Please login.")
        return redirect("login")

    return render(request, "register.html")


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard_view(request):
    #Sample Visits Only
    visits = [
        {
            "code": "LIB123",
            "status": "Active",
            "date": datetime(2025, 10, 5),
            "start_time": datetime.strptime("08:00", "%H:%M").time(),
            "end_time": datetime.strptime("10:00", "%H:%M").time(),
            "purpose": "Library Visit"
        },
        {
            "code": "GYM456",
            "status": "Upcoming",
            "date": datetime(2025, 10, 10),
            "start_time": datetime.strptime("14:00", "%H:%M").time(),
            "end_time": datetime.strptime("16:00", "%H:%M").time(),
            "purpose": "Gym Workout"
        }
    ]

    active_pass = len([v for v in visits if v["status"] == "Active"])
    upcoming_visits = len([v for v in visits if v["status"] == "Upcoming"])
    total_visits = len(visits)

    context = {
        "user_name": request.user.first_name or request.user.username,
        "active_pass": active_pass,
        "upcoming_visits": upcoming_visits,
        "total_visits": total_visits,
        "visits": visits
    }

    return render(request, "dashboard.html", context)