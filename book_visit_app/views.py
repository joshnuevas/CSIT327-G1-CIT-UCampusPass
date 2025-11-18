# book_visit_app/views.py
from django.shortcuts import render, redirect
import os
from dotenv import load_dotenv
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

    # Fetch user info using Django ORM
    try:
        try:
            user = User.objects.get(email=user_email)
            user_id = user.user_id
            first_name = user.first_name
            
            # Save first name in session for template use
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
            # Get form data
            purpose = request.POST.get('purpose_other') or request.POST.get('purpose')
            department = request.POST.get('department_other') or request.POST.get('department')
            visit_date_str = request.POST.get('visit_date')

            # Validate required fields
            if not all([purpose, department, visit_date_str]):
                messages.error(request, "Please fill in all required fields.")
                return redirect('book_visit_app:book_visit')

            # Validate visit date is not past and not Sunday
            visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").date()
            today = datetime.now().date()

            if visit_date < today:
                messages.error(request, "You cannot select a date that has already passed. Please select today or a future date.")
                return redirect('book_visit_app:book_visit')

            if visit_date.weekday() == 6:  # Sunday=6
                messages.error(request, "Visits cannot be scheduled on Sundays. Please select a weekday (Monday-Saturday).")
                return redirect('book_visit_app:book_visit')

            # Generate unique visit code
            code = generate_visit_code(purpose)
            
            # Ensure code is unique
            while Visit.objects.filter(code=code).exists():
                code = generate_visit_code(purpose)

            # Create visit record using Django ORM
            try:
                visit = Visit(
                    user_id=user_id,
                    user_email=user_email,
                    code=code,
                    purpose=purpose,
                    department=department,
                    visit_date=visit_date,
                    start_time=None,  # Will be set when staff checks in
                    end_time=None,   # Will be set when staff checks out
                    status="Upcoming"
                )
                visit.save()

                # Log the visit booking
                actor = f"{first_name} ({user_email})"
                description = f"Booked a visit for {visit_date_str} in {department} for purpose '{purpose}'."
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
            messages.info(request, "Please save your visit code for check-in. The check-in and check-out times will be recorded by staff.")

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