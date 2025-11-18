"""
Walk-In Registration App Views
Handles registration of visitors who arrive without pre-booking
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from supabase import create_client
import os
import random
import string
from dotenv import load_dotenv
from datetime import datetime
import pytz
import logging

# Setup
logger = logging.getLogger(__name__)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
def walk_in_registration(request):
    """Register walk-in visitors who arrive without pre-booking"""
    staff_username = request.session['staff_username']
    staff_first_name = request.session.get('staff_first_name', 'Staff')
    
    if request.method == 'POST':
        try:
            # Get form data
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            purpose = request.POST.get('purpose_other') or request.POST.get('purpose')
            department = request.POST.get('department_other') or request.POST.get('department')

            # Validate required fields
            if not all([first_name, last_name, email, phone, purpose, department]):
                messages.error(request, "Please fill in all required fields.")
                return redirect('walk_in_app:registration')

            # Generate visit code
            purpose_prefix = purpose[:3].upper() if purpose else "WLK"
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            visit_code = f"CIT-{purpose_prefix}-{random_str}"

            # Set visit times - walk-ins are checked in immediately
            now = datetime.now(PHILIPPINES_TZ)
            start_time = now.strftime('%H:%M:%S')
            visit_date = now.strftime('%Y-%m-%d')

            # Create visitor name
            visitor_name = f"{first_name} {last_name}"

            # Insert visit record
            visit_data = {
                "user_email": email,
                "code": visit_code,
                "purpose": purpose,
                "department": department,
                "visit_date": visit_date,
                "start_time": start_time,
                "end_time": None,  # Will be set when staff checks out
                "status": "Active",  # Automatically checked in
                "created_at": now.isoformat()
            }
            
            supabase.table("visits").insert(visit_data).execute()
            
            # Create log entry
            log_entry = {
                "actor": f"{staff_first_name} ({staff_username})",
                "action_type": "Walk-In Registration",
                "description": f"Registered walk-in visitor {visitor_name} ({email}) for {purpose} at {department}. Visit code: {visit_code}",
                "actor_role": "Staff",
                "created_at": now.isoformat()
            }
            supabase.table("system_logs").insert(log_entry).execute()
            
            # Success - show confirmation
            context = {
                'success': True,
                'visit_code': visit_code,
                'visitor_name': visitor_name,
                'visitor_email': email,
                'visitor_phone': phone,
                'purpose': purpose,
                'department': department,
            }
            
            logger.info(f"Walk-in visitor registered by {staff_username}: {visit_code}")
            return render(request, 'walk_in_app/walk_in_registration.html', context)
            
        except Exception as e:
            logger.error(f"Error in walk-in registration: {str(e)}")
            messages.error(request, "An error occurred during registration.")
            return redirect('walk_in_app:registration')
    
    # GET request - show form
    context = {
        'staff_first_name': staff_first_name,
        'form_data': {},
        'success': False,
    }
    return render(request, 'walk_in_app/walk_in_registration.html', context)