from django.shortcuts import render, redirect
from supabase import create_client
import os
from dotenv import load_dotenv
from django.contrib import messages
import random
import string
from django.core.mail import send_mail
from datetime import datetime, time
from django.conf import settings
import logging

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

def send_confirmation_email(user_email, first_name, visit_details, code):
    """
    Send confirmation email with proper error handling.
    Returns True if sent successfully, False otherwise.
    """
    print("\n" + "="*60)
    print("ATTEMPTING TO SEND EMAIL")
    print("="*60)
    print(f"To: {user_email}")
    print(f"First Name: {first_name}")
    print(f"Visit Code: {code}")
    
    # Skip email if not configured
    email_host_user = getattr(settings, 'EMAIL_HOST_USER', None)
    print(f"EMAIL_HOST_USER from settings: {email_host_user}")
    
    if not email_host_user:
        logger.warning("Email not configured. Skipping email send.")
        print("❌ EMAIL_HOST_USER is not configured!")
        print("="*60 + "\n")
        return False
    
    print(f"✓ EMAIL_HOST_USER is configured: {email_host_user}")
    
    subject = "CIT-U CampusPass | Visit Confirmation"
    message = (
        f"Hi {first_name},\n\n"
        f"Your visit has been successfully booked!\n\n"
        f"📅 Date: {visit_details['date']}\n"
        f"🕒 Time: {visit_details['start_time']} - {visit_details['end_time']}\n"
        f"🏢 Department: {visit_details['department']}\n"
        f"🎯 Purpose: {visit_details['purpose']}\n"
        f"🔑 Visit Code: {code}\n\n"
        f"Please present this visit code upon arrival.\n"
        f"Thank you for using CIT-U CampusPass!"
    )
    
    print(f"Subject: {subject}")
    print(f"From: {settings.DEFAULT_FROM_EMAIL}")
    print(f"To: {user_email}")
    print("Sending email synchronously...")
    
    try:
        result = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )
        print(f"✅ send_mail() returned: {result}")
        print(f"✅ Email sent successfully!")
        logger.info(f"Confirmation email sent to {user_email}")
        print("="*60 + "\n")
        return True
    except Exception as e:
        print(f"❌ EXCEPTION OCCURRED: {type(e).__name__}")
        print(f"❌ Error message: {str(e)}")
        logger.error(f"Failed to send email to {user_email}: {str(e)}")
        logger.exception("Full exception traceback:")
        print("="*60 + "\n")
        return False

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
                logger.info(f"Visit booked successfully for user {user_email} with code {code}")
            except Exception as e:
                logger.error(f"Database error while booking visit: {str(e)}")
                messages.error(request, "Failed to book visit. Please try again later.")
                return redirect('book_visit_app:book_visit')

            # Prepare visit details for email
            visit_details = {
                'date': visit_date_str,
                'start_time': start_time,
                'end_time': end_time,
                'department': department,
                'purpose': purpose
            }

            # Try to send confirmation email (SYNCHRONOUSLY - waits for completion)
            email_sent = send_confirmation_email(user_email, first_name, visit_details, code)

            # Show appropriate success message
            if email_sent:
                messages.success(request, f"Visit booked successfully! A confirmation email has been sent to {user_email}.")
            else:
                messages.success(request, f"Visit booked successfully! Your visit code is: {code}")
                messages.info(request, "Note: Confirmation email could not be sent, but your visit is confirmed.")

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