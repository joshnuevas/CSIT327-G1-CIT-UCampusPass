from django.shortcuts import render, redirect
from django.utils.timezone import now as django_now
from datetime import date, timedelta
import calendar
from dashboard_app.models import Visit
import pytz

PHILIPPINES_TZ = pytz.timezone('Asia/Manila')

def calendar_view(request):
    if 'user_email' not in request.session:
        return redirect('login_app:login')

    user_email = request.session['user_email']

    now_ph = django_now().astimezone(PHILIPPINES_TZ)
    today = now_ph.date()
    max_booking_date = today + timedelta(days=7)

    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except ValueError:
        year = today.year
        month = today.month

    cal = calendar.Calendar(firstweekday=6)
    weeks = cal.monthdatescalendar(year, month)

    start_date = weeks[0][0]
    end_date = weeks[-1][-1]

    visits = Visit.objects.filter(
        user_email=user_email,
        visit_date__range=[start_date, end_date]
    )

    visits_by_date = {}
    for visit in visits:
        date_str = visit.visit_date.strftime("%Y-%m-%d")
        visits_by_date.setdefault(date_str, []).append(visit)

    first_day_curr = date(year, month, 1)
    prev_month_date = first_day_curr - timedelta(days=1)
    next_month_date = (first_day_curr + timedelta(days=32)).replace(day=1)

    context = {
        "user_first_name": request.session.get("user_first_name"),
        "user_email": user_email,
        "today": today,
        "max_booking_date": max_booking_date,      # 👈 pass to template
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "weeks": weeks,
        "visits_by_date": visits_by_date,
        "prev_year": prev_month_date.year,
        "prev_month": prev_month_date.month,
        "next_year": next_month_date.year,
        "next_month": next_month_date.month,
    }

    return render(request, "calendar_app/calendar.html", context)
