"""
Walk-In Registration App Views
Handles registration of visitors who arrive without pre-booking
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
import random
import string
from datetime import datetime
import pytz
import logging
import re

# Import Django models
from dashboard_app.models import Visit, SystemLog
from register_app.models import User

# Setup
logger = logging.getLogger(__name__)
PHILIPPINES_TZ = pytz.timezone('Asia/Manila')


def staff_required(view_func):
    """Decorator to ensure only staff can access"""
    def wrapper(request, *args, **kwargs):
        if 'staff_username' not in request.session:
            messages.warning(request, "Please log in as staff to access this page.")
            return redirect('login_app:login')
        return view_func(request, *args, **kwargs)
    return wrapper


@staff_required
@require_http_methods(["GET", "POST"])
def walk_in_registration(request):
    """
    Register walk-in visitors who arrive without pre-booking.
    - Creates a Visit row
    - Immediately marks status as 'Active' with current time as start_time.
    """
    staff_username = request.session['staff_username']
    staff_first_name = request.session.get('staff_first_name', 'Staff')

    if request.method == 'POST':
        try:
            # ----- Get form data ----- 
            first_name = (request.POST.get('first_name') or '').strip()
            last_name = (request.POST.get('last_name') or '').strip()
            email = (request.POST.get('email') or '').strip()
            phone = (request.POST.get('phone') or '').strip()

            # Department & purpose (no more *_other fields)
            department = (request.POST.get('department') or '').strip()
            purpose = (request.POST.get('purpose') or '').strip()

            # Preserve form data for re-render on error
            form_data = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
                'department': department,
                'purpose': purpose,
            }

            # ----- Validate required fields -----
            if not all([first_name, last_name, email, phone, department, purpose]):
                messages.error(request, "Please fill in all required fields.")
                context = {
                    'staff_first_name': staff_first_name,
                    'form_data': form_data,
                    'success': False,
                }
                return render(request, 'walk_in_app/walk_in_registration.html', context)

            # Strict phone validation: must be 11 digits, start with 09
            if not re.fullmatch(r"09\d{9}", phone):
                messages.error(
                    request,
                    "Please enter a valid 11-digit mobile number starting with 09 (e.g., 09171234567)."
                )
                context = {
                    'staff_first_name': staff_first_name,
                    'form_data': form_data,
                    'success': False,
                }
                return render(request, 'walk_in_app/walk_in_registration.html', context)

            # ----- Generate visit code (purpose-based) -----
            purpose_prefix = purpose[:3].upper() if purpose else "WLK"
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            visit_code = f"CIT-{purpose_prefix}-{random_str}"

            # Ensure uniqueness (simple retry up to a few times)
            attempts = 0
            while Visit.objects.filter(code=visit_code).exists() and attempts < 5:
                attempts += 1
                random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                visit_code = f"CIT-{purpose_prefix}-{random_str}"

            if Visit.objects.filter(code=visit_code).exists():
                logger.error("Unable to generate unique visit code for walk-in visitor.")
                messages.error(request, "Failed to generate a unique visit code. Please try again.")
                context = {
                    'staff_first_name': staff_first_name,
                    'form_data': form_data,
                    'success': False,
                }
                return render(request, 'walk_in_app/walk_in_registration.html', context)

            # ----- Set visit times - walk-ins are checked in immediately -----
            now = datetime.now(PHILIPPINES_TZ)
            start_time = now.time()
            visit_date = now.date()

            visitor_name = f"{first_name} {last_name}"

            # Insert visit record using Django ORM
            visit = Visit(
                user_email=email,
                code=visit_code,
                purpose=purpose,
                department=department,
                visit_date=visit_date,
                start_time=start_time,
                end_time=None,     # Will be set on check-out
                status="Active",   # Automatically checked in
                user_id=None       # Walk-in visitors may not have user account
            )
            visit.save()

            # Create log entry using Django ORM
            log_entry = SystemLog(
                actor=f"{staff_first_name} ({staff_username})",
                action_type="Walk-In Registration",
                description=(
                    f"Registered walk-in visitor {visitor_name} ({email}) "
                    f"for {purpose} at {department}. Visit code: {visit_code}"
                ),
                actor_role="Staff",
                created_at=now
            )
            log_entry.save()

            logger.info(f"Walk-in visitor registered by {staff_username}: {visit_code}")

            # Success context
            context = {
                'success': True,
                'visit_code': visit_code,
                'visitor_name': visitor_name,
                'visitor_email': email,
                'visitor_phone': phone,
                'purpose': purpose,
                'department': department,
            }
            return render(request, 'walk_in_app/walk_in_registration.html', context)

        except Exception as e:
            logger.error(f"Error in walk-in registration: {str(e)}")
            messages.error(request, "An error occurred during registration.")
            context = {
                'staff_first_name': staff_first_name,
                'form_data': locals().get('form_data', {}),
                'success': False,
            }
            return render(request, 'walk_in_app/walk_in_registration.html', context)

    # GET request - show blank form
    context = {
        'staff_first_name': staff_first_name,
        'form_data': {},
        'success': False,
    }
    return render(request, 'walk_in_app/walk_in_registration.html', context)
