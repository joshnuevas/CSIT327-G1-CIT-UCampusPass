from django.shortcuts import render, redirect
from supabase import create_client
import os
from dotenv import load_dotenv
from django.contrib import messages
import random
import string
from datetime import datetime, time
import logging
from manage_reports_logs_app import services as logs_services

# Setup logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_visit_code(purpose):
    """Generate a unique visit code based on purpose."""
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    purpose_prefix = purpose[:3].upper() if purpose else "VIS"
    return f"CIT-{purpose_prefix}-{random_str}"

def book_visit_view(request):
    # Redirect if not logged in
    if 'user_email' not in request.session:
        messages.warning(request, "Please log in to book a visit.")
        return redirect('login_app:login')

    user_email = request.session['user_email']

    # Fetch user info from Supabase
    try:
        user_resp = supabase.table("users").select("user_id", "first_name").eq("email", user_email).execute()
        if not user_resp.data:
            messages.error(request, "User not found. Please log in again.")
            return redirect('login_app:login')
        
        user = user_resp.data[0]
        user_id = user['user_id']
        first_name = user['first_name']
        
        # Save first name in session for template use
        request.session['user_first_name'] = first_name
    except Exception as e:
        logger.error(f"Error fetching user data: {str(e)}")
        messages.error(request, "An error occurred. Please try again.")
        return redirect('login_app:login')

    if request.method == 'POST':
        try:
            # Get form data
            purpose = request.POST.get('purpose_other') or request.POST.get('purpose')
            department = request.POST.get('department_other') or request.POST.get('department')
            visit_date_str = request.POST.get('visit_date')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')

            # Validate required fields
            if not all([purpose, department, visit_date_str, start_time, end_time]):
                messages.error(request, "Please fill in all required fields.")
                return redirect('book_visit_app:book_visit')

            # Validate visit date is a weekday
            visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").date()
            if visit_date.weekday() >= 5:  # Saturday=5, Sunday=6
                messages.error(request, "Visits cannot be scheduled on weekends. Please select a weekday.")
                return redirect('book_visit_app:book_visit')

            # Validate visit time is within allowed hours (7:30 AM - 9:00 PM)
            try:
                visit_start = datetime.strptime(start_time, "%H:%M").time()
                visit_end = datetime.strptime(end_time, "%H:%M").time()
                
                start_allowed = time(7, 30)
                end_allowed = time(21, 0)
                
                if not (start_allowed <= visit_start and visit_end <= end_allowed):
                    messages.error(request, "Visits must be scheduled between 7:30 AM and 9:00 PM.")
                    return redirect('book_visit_app:book_visit')
                
                if visit_start >= visit_end:
                    messages.error(request, "End time must be after start time.")
                    return redirect('book_visit_app:book_visit')
            except ValueError:
                messages.error(request, "Invalid time format. Please try again.")
                return redirect('book_visit_app:book_visit')

            # Generate visit code
            code = generate_visit_code(purpose)

            # Insert visit record into database
            try:
                supabase.table("visits").insert({
                    "user_id": user_id,
                    "user_email": user_email,
                    "code": code,
                    "purpose": purpose,
                    "department": department,
                    "visit_date": visit_date_str,
                    "start_time": start_time,
                    "end_time": end_time,
                    "status": "Upcoming"
                }).execute()
                # Log the visit booking
                actor = f"{first_name} ({user_email})"
                description = f"Booked a visit for {visit_date_str} from {start_time} to {end_time} in {department} for purpose '{purpose}'."
                try:
                    logs_services.create_log(
                        actor=actor,
                        action_type="Visit Booking",
                        description=description,
                        actor_role="Visitor"
                    )
                except Exception as log_error:
                    logger.error(f"Failed to log visit booking: {str(log_error)}")

                logger.info(f"Visit booked successfully for user {user_email} with code {code}")
            except Exception as e:
                logger.error(f"Database error while booking visit: {str(e)}")
                messages.error(request, "Failed to book visit. Please try again later.")
                return redirect('book_visit_app:book_visit')

            # Show success message with visit code
            messages.success(request, f"Visit booked successfully! Your visit code is: {code}")
            messages.info(request, "Please save your visit code for check-in.")

            return redirect('dashboard_app:dashboard')

        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            messages.error(request, "Invalid date or time format. Please check your input.")
            return redirect('book_visit_app:book_visit')
        except Exception as e:
            logger.error(f"Unexpected error during booking: {str(e)}")
            messages.error(request, "An unexpected error occurred. Please try again.")
            return redirect('book_visit_app:book_visit')

    # GET request - render the booking form
    context = {
        "user_first_name": first_name
    }
    return render(request, 'book_visit_app/book_visit.html', context)