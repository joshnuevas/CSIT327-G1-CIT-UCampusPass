"""
Walk-In Registration App Views
Handles registration of visitors who arrive without pre-booking
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils import timezone

import random
import string
from datetime import datetime, time as dtime
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
    - Enforces:
        * Walk-in registration allowed only from 7:30 AM to 9:00 PM (PH time)
        * If email/phone belong to an existing User, other fields must match.
        * No duplicate phone across different users.
        * If visitor already has an Active pass, block new walk-in registration.
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

            # ----- Time-based restriction: 7:30 AM–9:00 PM (PH time) -----
            now_aware = timezone.now().astimezone(PHILIPPINES_TZ)
            current_t = now_aware.time()

            start_allowed = dtime(7, 30)   # 7:30 AM
            end_allowed = dtime(21, 0)     # 9:00 PM

            if not (start_allowed <= current_t < end_allowed):
                messages.error(
                    request,
                    "⏰ Walk-in registration is only allowed from 7:30 AM to 9:00 PM. "
                    "Please advise the visitor to return during operating hours."
                )
                context = {
                    'staff_first_name': staff_first_name,
                    'form_data': form_data,
                    'success': False,
                }
                return render(request, 'walk_in_app/walk_in_registration.html', context)

            # ----- Basic required field validation -----
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
                    "Please enter a valid 11-digit mobile number starting with 09 "
                    "(e.g., 09171234567)."
                )
                context = {
                    'staff_first_name': staff_first_name,
                    'form_data': form_data,
                    'success': False,
                }
                return render(request, 'walk_in_app/walk_in_registration.html', context)

            # =====================================================
            #  EMAIL + PHONE CONSISTENCY (NO DUPLICATES)
            # =====================================================

            def norm(s: str) -> str:
                return (s or "").strip().lower()

            normalized_phone = re.sub(r"\D", "", phone or "")

            # 1) Try match by email
            user_by_email = User.objects.filter(email__iexact=email).first()

            # 2) Try match by phone (assume stored as 09xxxxxxxxx in DB)
            users_by_phone = list(User.objects.filter(phone=phone))

            # If same phone is used by multiple users -> hard stop
            if len(users_by_phone) > 1:
                messages.error(
                    request,
                    (
                        "This mobile number is associated with multiple registered users. "
                        "Please verify the visitor’s information with the registrar before "
                        "proceeding with walk-in registration."
                    )
                )
                context = {
                    'staff_first_name': staff_first_name,
                    'form_data': form_data,
                    'success': False,
                }
                return render(request, 'walk_in_app/walk_in_registration.html', context)

            user_by_phone = users_by_phone[0] if users_by_phone else None

            # If email and phone both match but point to different accounts -> hard stop
            if user_by_email and user_by_phone and user_by_email != user_by_phone:
                messages.error(
                    request,
                    (
                        "The provided email and mobile number are registered under "
                        "different user records. Please verify the visitor’s details."
                    )
                )
                context = {
                    'staff_first_name': staff_first_name,
                    'form_data': form_data,
                    'success': False,
                }
                return render(request, 'walk_in_app/walk_in_registration.html', context)

            # Use whichever matched (email preferred, then phone)
            existing_user = user_by_email or user_by_phone

            # If we found a registered user, all fields must match that record
            if existing_user:
                mismatches = []

                if norm(existing_user.first_name) != norm(first_name):
                    mismatches.append("first name")

                if norm(existing_user.last_name) != norm(last_name):
                    mismatches.append("last name")

                if norm(existing_user.email) != norm(email):
                    mismatches.append("email")

                db_phone_digits = re.sub(r"\D", "", existing_user.phone or "")
                if db_phone_digits and normalized_phone and db_phone_digits != normalized_phone:
                    mismatches.append("mobile number")

                if mismatches:
                    pretty_fields = ", ".join(mismatches)
                    messages.error(
                        request,
                        (
                            "This visitor is already registered. "
                            f"The {pretty_fields} you entered do not match our records. "
                            "Please verify the information with the visitor."
                        )
                    )
                    context = {
                        'staff_first_name': staff_first_name,
                        'form_data': form_data,
                        'success': False,
                    }
                    return render(request, 'walk_in_app/walk_in_registration.html', context)

            # ----- Block if visitor already has an Active pass -----
            active_visit = Visit.objects.filter(
                user_email__iexact=email,
                status="Active"
            ).order_by('-visit_date', '-start_time').first()

            if active_visit:
                messages.error(
                    request,
                    (
                        "This visitor already has an active campus pass "
                        f"(Code: {active_visit.code}). "
                        "They must use their existing pass or be checked out before "
                        "registering another walk-in visit."
                    )
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
            visit_date = now_aware.date()
            start_time = now_aware.time()

            visitor_name = f"{first_name} {last_name}"

            # Link visit to existing User if found
            user_id_value = existing_user.user_id if existing_user else None

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
                user_id=user_id_value
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
                created_at=now_aware,  # stored as PH time
            )
            log_entry.save()

            logger.info(f"Walk-in visitor registered by {staff_username}: {visit_code}")

            # Pre-format display string in PH time, desired format: "Dec 07, 2025 06:46 PM"
            visit_datetime_display = now_aware.strftime("%b %d, %Y %I:%M %p")

            # Success context
            context = {
                'success': True,
                'visit_code': visit_code,
                'visitor_name': visitor_name,
                'visitor_email': email,
                'visitor_phone': phone,
                'purpose': purpose,
                'department': department,
                'visit_datetime_display': visit_datetime_display,
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
