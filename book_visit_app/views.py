from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings

import random
import string
from datetime import datetime
import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from manage_reports_logs_app import services as logs_services
from dashboard_app.models import Visit
from register_app.models import User

# Setup logging
logger = logging.getLogger(__name__)


def generate_visit_code(purpose: str) -> str:
    """Generate a unique visit code EX: CIT-ADM-A1B2C."""
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    prefix = (purpose or "VIS")[:3].upper()
    return f"CIT-{prefix}-{random_str}"


def book_visit_view(request):
    """Visitor books a campus visit with email confirmation."""

    # Must be logged in
    if "user_email" not in request.session:
        messages.warning(request, "Please log in first to book a visit.")
        return redirect("login_app:login")

    # Logged-in user
    user_email = request.session["user_email"]

    try:
        user = User.objects.get(email=user_email)
        user_id = user.user_id
        first_name = user.first_name
        request.session["user_first_name"] = first_name
    except User.DoesNotExist:
        messages.error(request, "User not found. Please log in again.")
        return redirect("login_app:login")
    except Exception as e:
        logger.error(f"Error retrieving user: {str(e)}")
        messages.error(request, "Unexpected error. Please try again.")
        return redirect("login_app:login")

    # POST = form submission
    if request.method == "POST":
        try:
            # Department and purpose (including 'Other')
            raw_department = (request.POST.get("department_other") or request.POST.get("department") or "").strip()
            raw_purpose = (request.POST.get("purpose_other") or request.POST.get("purpose") or "").strip()
            visit_date_str = (request.POST.get("visit_date") or "").strip()

            # Validate fields
            if not raw_purpose or not raw_department or not visit_date_str:
                messages.error(request, "Please complete all required fields.")
                return redirect("book_visit_app:book_visit")

            # Convert date
            try:
                visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Invalid date format.")
                return redirect("book_visit_app:book_visit")

            # Date checks
            today = datetime.now().date()

            if visit_date < today:
                messages.error(request, "Past dates are not allowed.")
                return redirect("book_visit_app:book_visit")

            # Sunday = 6
            if visit_date.weekday() == 6:
                messages.error(request, "Visits cannot be scheduled on Sundays.")
                return redirect("book_visit_app:book_visit")

            # Generate unique visit code
            code = generate_visit_code(raw_purpose)
            attempts = 0
            while Visit.objects.filter(code=code).exists() and attempts < 5:
                attempts += 1
                code = generate_visit_code(raw_purpose)

            if Visit.objects.filter(code=code).exists():
                messages.error(request, "Could not generate a unique visit code. Try again.")
                return redirect("book_visit_app:book_visit")

            # Create visit record
            try:
                visit = Visit(
                    user_id=user_id,
                    user_email=user_email,
                    code=code,
                    purpose=raw_purpose,
                    department=raw_department,
                    visit_date=visit_date,
                    start_time=None,
                    end_time=None,
                    status="Upcoming",
                )
                visit.save()
            except Exception as db_error:
                logger.error(f"Database error: {str(db_error)}")
                messages.error(request, "Failed to save visit. Please try again.")
                return redirect("book_visit_app:book_visit")

            # =============================
            # SEND EMAIL USING SENDGRID API
            # =============================
            try:
                subject = "CIT-U CampusPass • Visit Booking Confirmation"
                visit_date_human = visit_date.strftime("%B %d, %Y")

                text_body = (
                    f"Hi {first_name},\n\n"
                    f"Your campus visit has been successfully booked.\n\n"
                    f"Visit Details:\n"
                    f"• Visit Code: {code}\n"
                    f"• Visit Date: {visit_date_human}\n"
                    f"• Department: {raw_department}\n"
                    f"• Purpose: {raw_purpose}\n\n"
                    f"Please save your visit code.\n"
                    f"You will present this during check-in.\n\n"
                    f"Thank you,\n"
                    f"CIT-U CampusPass System"
                )

                message = Mail(
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to_emails=user_email,
                    subject=subject,
                    plain_text_content=text_body
                )

                sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                sg.send(message)

                logger.info(f"SendGrid email sent to {user_email}")

            except Exception as email_error:
                logger.error(f"SendGrid email failed: {str(email_error)}")
                messages.warning(
                    request,
                    f"Visit booked but email could not be sent. Your visit code is {code}."
                )

            # Log user action
            try:
                logs_services.create_log(
                    actor=f"{first_name} ({user_email})",
                    action_type="Visit Booking",
                    description=f"Booked visit for {visit_date_str} in {raw_department} for '{raw_purpose}'.",
                    actor_role="Visitor",
                )
            except Exception as log_error:
                logger.error(f"Log creation failed: {str(log_error)}")

            # Success messages
            messages.success(request, f"Visit booked successfully! Your code is: {code}")
            messages.info(request, "A confirmation email has been sent to your inbox.")

            return redirect("dashboard_app:dashboard")

        except Exception as e:
            logger.error(f"Unexpected error during booking: {str(e)}")
            messages.error(request, "Unexpected error. Please try again.")
            return redirect("book_visit_app:book_visit")

    # GET request = show form
    return render(request, "book_visit_app/book_visit.html", {
        "user_first_name": first_name
    })
