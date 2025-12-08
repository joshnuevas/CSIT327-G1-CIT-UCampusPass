"""
Visitor Search App Views
Handles visitor search and detailed visitor information
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q
import os
from dotenv import load_dotenv
from datetime import date, timedelta
import logging

# Import Django models
from dashboard_app.models import Visit
from register_app.models import User

# Setup
logger = logging.getLogger(__name__)

def staff_required(view_func):
    """Decorator to ensure only staff can access"""
    def wrapper(request, *args, **kwargs):
        if 'staff_username' not in request.session:
            messages.warning(request, "Please log in as staff to access this page.")
            return redirect('login_app:login')
        return view_func(request, *args, **kwargs)
    return wrapper


@staff_required
def visitor_search(request):
    """Search visitors and show their next valid visit (upcoming or active)."""

    staff_first_name = request.session.get("staff_first_name", "Staff")
    query = request.GET.get("query", "").strip()
    filter_type = request.GET.get("filter", "all")

    # No search query → render empty state
    if not query:
        return render(request, "visitor_search_app/visitor_search.html", {
            "staff_first_name": staff_first_name,
            "query": "",
            "filter": filter_type,
            "results": []
        })

    results = []
    today = date.today()

    # Load users and visits efficiently
    users = User.objects.all()
    visits = Visit.objects.all()

    # Map email → user info
    users_dict = {
        u.email.lower(): {
            "first_name": u.first_name,
            "last_name": u.last_name,
            "full_name": f"{u.first_name} {u.last_name}".strip()
        }
        for u in users
    }

    # --- STEP 1: MATCH SEARCH QUERY (NAME + EMAIL ONLY) ---
    q = query.lower()
    matched = []

    for v in visits:
        email = (v.user_email or "").lower()
        name = users_dict.get(email, {}).get("full_name", "").lower()

        # Only match: name OR email
        if q in email or q in name:
            matched.append({
                "visit_id": v.visit_id,
                "user_email": v.user_email,
                "code": v.code,
                "purpose": v.purpose,
                "department": v.department,
                "visit_date": v.visit_date,
                "start_time": v.start_time,
                "end_time": v.end_time,
                "status": v.status,
                "created_at": v.created_at
            })

    # --- STEP 2: APPLY FILTERS ---
    if filter_type == "active":
        matched = [v for v in matched if v["status"] == "Active"]

    elif filter_type == "today":
        matched = [v for v in matched if v["visit_date"] == today]

    elif filter_type == "week":
        monday = today - timedelta(days=today.weekday())
        matched = [v for v in matched if v["visit_date"] >= monday]

    # --- STEP 3: GROUP BY USER (email) ---
    grouped = {}

    for v in matched:
        email = v["user_email"]

        if email not in grouped:
            uinfo = users_dict.get(email.lower(), {})
            grouped[email] = {
                "user_email": email,
                "visitor_name": uinfo.get("full_name", email.split("@")[0].title()),
                "first_name": uinfo.get("first_name", ""),
                "last_name": uinfo.get("last_name", ""),
                "visits": []
            }

        grouped[email]["visits"].append(v)

    # --- STEP 4: SELECT NEXT VISIT + DETERMINE STATUS ---
    for email, data in grouped.items():
        visit_list = sorted(data["visits"], key=lambda x: x["visit_date"])

        today = date.today()

        # 1️⃣ PRIORITY: Active today
        active_today = next(
            (v for v in visit_list if v["visit_date"] == today and v["status"] == "Active"),
            None
        )

        # 2️⃣ Next: Upcoming (today or future) and NOT completed
        upcoming = next(
            (v for v in visit_list
            if v["visit_date"] >= today and v["status"] != "Completed"),
            None
        )

        # 3️⃣ If NO valid next visit → show nothing (all completed)
        next_visit = active_today or upcoming

        # If everything was completed, fallback to None
        if not next_visit:
            # OPTIONAL: show last completed visit instead of None
            next_visit = max(visit_list, key=lambda x: x["visit_date"])

        # Determine final display status (status wins over date)
        status = next_visit["status"]

        if status == "Active":
            display_status = "Active"
        elif status == "Completed":
            display_status = "Completed"
        elif status in ["Cancelled", "Expired"]:
            display_status = status  # or map to your own label
        else:
            # Only fall back to date logic if it's not a terminal state
            if next_visit["visit_date"] > today:
                display_status = "Upcoming"
            elif next_visit["visit_date"] == today:
                # could be "Upcoming" or "Active" based on your rules
                display_status = "Upcoming"
            else:
                display_status = status or "Completed"

        results.append({
            "user_email": email,
            "visitor_name": data["visitor_name"],
            "first_name": data["first_name"],
            "last_name": data["last_name"],
            "current_visit": next_visit,
            "current_status": display_status,
            "visit_history": sorted(data["visits"], key=lambda x: x["visit_date"], reverse=True),
            "total_visits": len(data["visits"])
        })


    # Sort results by status priority
    priority = {"Active": 0, "Upcoming": 1, "Completed": 2, "Expired": 3}
    results.sort(key=lambda r: priority.get(r["current_status"], 99))

    return render(request, "visitor_search_app/visitor_search.html", {
        "staff_first_name": staff_first_name,
        "query": query,
        "filter": filter_type,
        "results": results
    })

@staff_required
def visitor_detail(request):
    """Show detailed information about a specific visitor"""
    staff_first_name = request.session.get('staff_first_name', 'Staff')
    visitor_email = request.GET.get('email', '').strip()
    
    if not visitor_email:
        messages.error(request, "Visitor email is required.")
        return redirect('visitor_search_app:search')
    
    try:
        # Get user information using Django ORM
        try:
            user = User.objects.get(email=visitor_email)
            first_name = user.first_name
            last_name = user.last_name
        except User.DoesNotExist:
            messages.error(request, "Visitor not found in system.")
            return redirect('visitor_search_app:search')
        
        # Get all visits for this visitor using Django ORM
        visits = Visit.objects.filter(user_email=visitor_email)
        
        if not visits:
            messages.warning(request, "No visits found for this visitor.")
            # Still show the visitor profile even if no visits
        
        # Convert visits to list of dictionaries for template
        visits_list = []
        for visit in visits:
            visits_list.append({
                'visit_id': visit.visit_id,
                'user_email': visit.user_email,
                'code': visit.code,
                'purpose': visit.purpose,
                'department': visit.department,
                'visit_date': visit.visit_date,
                'start_time': visit.start_time,
                'end_time': visit.end_time,
                'status': visit.status,
                'created_at': visit.created_at
            })
        
        # Sort visits by date descending (latest first)
        visits_list.sort(key=lambda x: x.get('visit_date', ''), reverse=True)

        # Calculate statistics
        total_visits = len(visits_list)
        completed_visits = len([v for v in visits_list if v.get('status') == 'Completed'])
        current_visit = next((v for v in visits_list if v.get('status') in ['Active', 'Upcoming']), None)
        last_visit_date = visits_list[0].get('visit_date') if visits_list else None

        # EARLIEST visit for "Member Since"
        member_since = None
        if visits_list:
            dates_only = [v['visit_date'] for v in visits_list if v.get('visit_date')]
            if dates_only:
                member_since = min(dates_only)

        context = {
            'staff_first_name': staff_first_name,
            'visitor_email': visitor_email,
            'first_name': first_name,
            'last_name': last_name,
            'visitor_name': f"{first_name} {last_name}",  # Also provide combined for fallback
            'total_visits': total_visits,
            'completed_visits': completed_visits,
            'current_visit': current_visit,
            'last_visit_date': last_visit_date,
            'member_since': member_since,          # ✅ new
            'visit_history': visits_list,
        }
        
        return render(request, 'visitor_search_app/visitor_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error loading visitor detail: {str(e)}")
        messages.error(request, "An error occurred loading visitor details.")
        return redirect('visitor_search_app:search')