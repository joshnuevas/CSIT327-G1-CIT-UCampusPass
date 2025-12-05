from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone

import logging
import random
import string
import re
from datetime import datetime, timedelta

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from manage_reports_logs_app import services as logs_services
from dashboard_app.models import Visit
from register_app.models import User

# Setup logging
logger = logging.getLogger(__name__)

DEPARTMENT_CODE_MAP = {
    # 🎓 Academic Colleges / Departments
    "College of Engineering and Architecture (CEA)": "CEA",
    "College of Computer Studies (CCS)": "CCS",
    "College of Management, Business and Accountancy (CMBA)": "CMBA",
    "College of Arts, Sciences and Education (CASE)": "CASE",
    "College of Nursing and Allied Health Sciences (CNAHS)": "CNAHS",
    "College of Criminal Justice (CCJ)": "CCJ",
    "Senior High School Department": "SHS",
    "Basic Education Department (BED)": "BED",

    # 🏫 Academic Support Units
    "Learning Resource and Activity Center (LRAC)": "LRAC",
    "Student Success Office (SSO)": "SSO",
    "Office of Student Affairs (OSA)": "OSA",
    "Office of Student Discipline (OSD)": "OSD",
    "Curriculum and Instruction Office (CIO)": "CIO",
    "Center for Teaching and Learning (CTL)": "CTL",
    "Center for Research and Development (CRD)": "CRD",
    "Center for Community Extension (CCE)": "CCE",
    "Guidance Services Office (GSO)": "GSO",

    # 💰 Administrative & Finance Offices
    "Office of Admissions and Scholarships (OAS)": "OAS",
    "University Registrar's Office (URO)": "URO",
    "Finance and Accounting Office (FAO)": "FAO",
    "Cashier's Office": "CASH",
    "Human Resource Department (HRD)": "HRD",
    "Property and Supply Office (PSO)": "PSO",
    "Physical Plant Office (PPO)": "PPO",
    "ICT / MIS Office": "MIS",
    "Purchasing Office": "PURC",
    "Maintenance Office": "MAIN",
    "Janitorial Services Office": "JAN",

    # 🌐 External & Institutional Offices
    "Institutional Planning and Development Office (IPDO)": "IPDO",
    "Networking, Linkages & Relations (NLR)": "NLR",
    "Public Relations and Communications Office (PRCO)": "PRCO",
    "Quality Assurance Office (QAO)": "QAO",
    "Alumni Affairs Office (AAO)": "AAO",
    "Industry-Academe Linkage Office (IALO)": "IALO",
    "Technology Business Incubation Office (TBI Office)": "TBI",
    "Internal Audit Office (IAO)": "IAO",

    # 🛡 Campus Services
    "Security Office": "SEC",
    "Clinic / Health Services Office": "CLINIC",

    # 🏛 Executive Offices
    "Office of the University President": "OP",
    "Office of the Executive Vice President": "EVP",
    "Office of the VP for Academic Affairs (VPAA)": "VPAA",
    "Office of the VP for Administration (VPA)": "VPA",
    "Office of the VP for Finance (VPF)": "VPF",
    "Office of the VP for External Affairs (VPEA)": "VPEA",

    # Catch-all
    "Other": "OTH",
}


def generate_visit_code(department: str) -> str:
    """
    Generate a unique visit code, e.g. CIT-CCS-A1B2C.

    The middle part is always exactly 3 characters:
    - Prefer a mapped department code from DEPARTMENT_CODE_MAP
    - Otherwise derive from the department string.
    """
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

    dept_raw = (department or "VIS").strip()
    code_part = DEPARTMENT_CODE_MAP.get(dept_raw)

    # Case-insensitive match if direct lookup failed
    if not code_part:
        for name, abbr in DEPARTMENT_CODE_MAP.items():
            if dept_raw.lower() == name.lower():
                code_part = abbr
                break

    if not code_part:
        cleaned = re.sub(r"[^A-Za-z0-9]", "", dept_raw).upper()
    else:
        cleaned = re.sub(r"[^A-Za-z0-9]", "", str(code_part).upper())

    cleaned = cleaned or "VIS"
    code_part = cleaned[:3]  # ensure exactly 3 chars

    return f"CIT-{code_part}-{random_str}"


def _looks_like_nonsense(text: str) -> bool:
    """
    Simple heuristic to catch very obvious junk values like 'lol', 'asdf', etc.
    Not perfect, just blocks obvious garbage entries.
    """
    if not text:
        return True

    value = text.strip().lower()
    banned = {"lol", "test", "asdf", "qwerty", "hehe", "huhu", "???", "???."}

    if value in banned:
        return True

    if len(value) < 3:
        return True

    return False


def book_visit_view(request):
    """
    Visitor books a campus visit with email confirmation.

    Validations:
    - User must be logged in
    - Department and Purpose must be present and not obvious nonsense
    - Visit date must be today or future, not Sunday, and within 7 days
    - Only one active booking per user per day (excluding cancelled)
    - Uses SendGrid to send confirmation email
    - Logs action in reports/logs service
    """

    # User must be logged in
    if "user_email" not in request.session:
        messages.warning(request, "Please log in first to book a visit.")
        return redirect("login_app:login")

    user_email = request.session["user_email"]

    # Get user info
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
            # Department and purpose (including 'Other' overrides)
            raw_department = (
                request.POST.get("department_other")
                or request.POST.get("department")
                or ""
            ).strip()

            raw_purpose = (
                request.POST.get("purpose_other")
                or request.POST.get("purpose")
                or ""
            ).strip()

            visit_date_str = (request.POST.get("visit_date") or "").strip()

            # Basic required check
            if not raw_purpose or not raw_department or not visit_date_str:
                messages.error(request, "Please complete all required fields.")
                return redirect("book_visit_app:book_visit")

            # ===============================
            # VALIDATE DEPARTMENT
            # ===============================
            if len(raw_department) < 5 or _looks_like_nonsense(raw_department):
                messages.error(
                    request,
                    "Please provide a more descriptive department name (no test or random values)."
                )
                return redirect("book_visit_app:book_visit")

            # Allow letters, numbers, spaces and common punctuation
            if not re.match(r"^[A-Za-z0-9&()' .,/\\-]+$", raw_department):
                messages.error(
                    request,
                    "Department name contains invalid characters. "
                    "Please use letters, numbers, and basic punctuation only."
                )
                return redirect("book_visit_app:book_visit")

            # ===============================
            # VALIDATE PURPOSE
            # ===============================
            words = raw_purpose.split()
            if len(raw_purpose) < 10 or len(words) < 2 or _looks_like_nonsense(raw_purpose):
                messages.error(
                    request,
                    "Please provide a clear and descriptive purpose for your visit "
                    "(at least two words and not random text)."
                )
                return redirect("book_visit_app:book_visit")

            # ===============================
            # VALIDATE VISIT DATE
            # ===============================
            try:
                visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Invalid date format.")
                return redirect("book_visit_app:book_visit")

            # Use Django's local date (respects TIME_ZONE)
            today = timezone.localdate()
            max_date = today + timedelta(days=7)

            # No past dates
            if visit_date < today:
                messages.error(request, "Past dates are not allowed.")
                return redirect("book_visit_app:book_visit")

            # No more than 7 days ahead
            if visit_date > max_date:
                messages.error(
                    request,
                    "You can only book a visit up to 7 days in advance."
                )
                return redirect("book_visit_app:book_visit")

            # Sunday = 6 (Monday = 0)
            if visit_date.weekday() == 6:
                messages.error(request, "Visits cannot be scheduled on Sundays.")
                return redirect("book_visit_app:book_visit")

            # ===============================
            # CHECK FOR EXISTING BOOKING THAT DAY
            # ===============================
            existing_visit = (
                Visit.objects
                .filter(user_id=user_id, visit_date=visit_date)
                .exclude(status__iexact="Cancelled")
                .first()
            )

            if existing_visit:
                visit_date_human = visit_date.strftime("%B %d, %Y")
                messages.error(
                    request,
                    f"You already have a booking on {visit_date_human}. "
                    f"Please cancel your existing booking first before creating another one for the same day."
                )
                return redirect("book_visit_app:book_visit")

            # ===============================
            # GENERATE UNIQUE VISIT CODE
            # ===============================
            code = generate_visit_code(raw_department)
            attempts = 0

            while Visit.objects.filter(code=code).exists() and attempts < 5:
                attempts += 1
                code = generate_visit_code(raw_department)

            if Visit.objects.filter(code=code).exists():
                messages.error(request, "Could not generate a unique visit code. Please try again.")
                return redirect("book_visit_app:book_visit")

            # ===============================
            # CREATE VISIT RECORD
            # ===============================
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
                logger.error(f"Database error while saving visit: {str(db_error)}")
                messages.error(request, "Failed to save visit. Please try again.")
                return redirect("book_visit_app:book_visit")

            # ===============================
            # SEND EMAIL USING SENDGRID
            # ===============================
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
                    plain_text_content=text_body,
                )

                sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                sg.send(message)

                logger.info(f"SendGrid email sent to {user_email}")

            except Exception as email_error:
                logger.error(f"SendGrid email failed: {str(email_error)}")
                messages.warning(
                    request,
                    f"Visit booked but email could not be sent. "
                    f"Your visit code is {code}."
                )

            # ===============================
            # LOG USER ACTION
            # ===============================
            try:
                logs_services.create_log(
                    actor=f"{first_name} ({user_email})",
                    action_type="Visit Booking",
                    description=f"Booked visit for {visit_date_str} in {raw_department} for '{raw_purpose}'.",
                    actor_role="Visitor",
                )
            except Exception as log_error:
                logger.error(f"Log creation failed: {str(log_error)}")

            # ===============================
            # SUCCESS & REDIRECT
            # ===============================
            messages.success(request, f"Visit booked successfully! Your code is: {code}")
            messages.info(request, "A confirmation email has been sent to your inbox.")

            return redirect("dashboard_app:dashboard")

        except Exception as e:
            logger.error(f"Unexpected error during booking: {str(e)}")
            messages.error(request, "Unexpected error. Please try again.")
            return redirect("book_visit_app:book_visit")

    # GET request = show form
    return render(
        request,
        "book_visit_app/book_visit.html",
        {"user_first_name": first_name},
    )
