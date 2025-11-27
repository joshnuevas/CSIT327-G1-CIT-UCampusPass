from django.shortcuts import render, redirect
from django.contrib import messages
import random
import string
from datetime import datetime, time
import logging

from manage_reports_logs_app import services as logs_services

# Import Django models
from dashboard_app.models import Visit
from register_app.models import User

# Setup logging
logger = logging.getLogger(__name__)


def generate_visit_code(purpose: str) -> str:
    """
    Generate a unique visit code based on purpose.
    Example: CIT-ADM-AB12C
    """
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    purpose_prefix = (purpose or "VIS")[:3].upper()
    return f"CIT-{purpose_prefix}-{random_str}"


def book_visit_view(request):
    """
    Visitor: Book a visit.
    Handles:
    - Department dropdown + 'Other'
    - Purpose dropdown + 'Other'
    - Date validation (no past, no Sundays)
    - Creates Visit with status='Upcoming'
    """

    # Must be logged-in as visitor
    if 'user_email' not in request.session:
        messages.warning(request, "Please log in to book a visit.")
        return redirect('login_app:login')

    user_email = request.session['user_email']

    # Fetch user info
    try:
        user = User.objects.get(email=user_email)
        user_id = user.user_id
        first_name = user.first_name
        request.session['user_first_name'] = first_name
    except User.DoesNotExist:
        messages.error(request, "User not found. Please log in again.")
        return redirect('login_app:login')
    except Exception as e:
        logger.error(f"Error fetching user data: {str(e)}")
        messages.error(request, "An error occurred. Please try again.")
        return redirect('login_app:login')

    if request.method == 'POST':
        try:
            # Get form data (prefer *_other if filled)
            raw_purpose = (request.POST.get('purpose_other') or request.POST.get('purpose') or "").strip()
            raw_department = (request.POST.get('department_other') or request.POST.get('department') or "").strip()
            visit_date_str = (request.POST.get('visit_date') or "").strip()

            # Validate fields
            if not raw_department or not raw_purpose or not visit_date_str:
                messages.error(request, "Please fill in all required fields.")
                return redirect('book_visit_app:book_visit')

            # Parse and validate visit date
            try:
                visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Invalid date format. Please select a valid date.")
                return redirect('book_visit_app:book_visit')

            today = datetime.now().date()

            if visit_date < today:
                messages.error(
                    request,
                    "You cannot select a date that has already passed. Please select today or a future date."
                )
                return redirect('book_visit_app:book_visit')

            # weekday(): Monday=0, Sunday=6
            if visit_date.weekday() == 6:
                messages.error(
                    request,
                    "Visits cannot be scheduled on Sundays. Please select a weekday (Monday-Saturday)."
                )
                return redirect('book_visit_app:book_visit')

            # Generate a unique visit code
            purpose_for_code = raw_purpose or "Visit"
            code = generate_visit_code(purpose_for_code)

            # Ensure uniqueness
            attempts = 0
            while Visit.objects.filter(code=code).exists() and attempts < 5:
                attempts += 1
                code = generate_visit_code(purpose_for_code)

            if Visit.objects.filter(code=code).exists():
                logger.error("Failed to generate unique visit code after multiple attempts.")
                messages.error(request, "Failed to generate a unique visit code. Please try again.")
                return redirect('book_visit_app:book_visit')

            # Create Visit row
            try:
                visit = Visit(
                    user_id=user_id,
                    user_email=user_email,
                    code=code,
                    purpose=raw_purpose,
                    department=raw_department,
                    visit_date=visit_date,
                    start_time=None,  # To be filled at check-in
                    end_time=None,    # To be filled at check-out
                    status="Upcoming"
                )
                visit.save()
            except Exception as db_error:
                logger.error(f"Database error while booking visit: {str(db_error)}")
                messages.error(request, "Failed to book visit. Please try again later.")
                return redirect('book_visit_app:book_visit')

            # Log the booking
            actor = f"{first_name} ({user_email})"
            description = f"Booked a visit for {visit_date_str} in {raw_department} for purpose '{raw_purpose}'."
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

            messages.success(request, f"Visit booked successfully! Your visit code is: {code}")
            messages.info(request, "Please save your visit code for check-in. Staff will record your check-in and check-out times.")

            # Redirect to visitor dashboard
            return redirect('dashboard_app:dashboard')

        except Exception as e:
            logger.error(f"Unexpected error during booking: {str(e)}")
            messages.error(request, "An unexpected error occurred. Please try again.")
            return redirect('book_visit_app:book_visit')

    # GET request → render booking form
    context = {
        "user_first_name": first_name
    }
    return render(request, 'book_visit_app/book_visit.html', context)
