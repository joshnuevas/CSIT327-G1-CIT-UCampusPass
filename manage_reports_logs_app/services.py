# manage_reports_logs_app/services.py

import logging
import pytz
from datetime import datetime
from django.conf import settings
from django.utils import timezone

# Import Django models
from dashboard_app.models import SystemLog, Visit
from register_app.models import User
from login_app.models import Administrator, FrontDeskStaff

logger = logging.getLogger(__name__)

# ==============================
# LOGS SERVICES
# ==============================

def _extract_identifier(actor_str):
    """Helper to extract username/email from 'Name (identifier)' format."""
    if '(' in actor_str and actor_str.endswith(')'):
        return actor_str.split('(')[-1].rstrip(')')
    return actor_str

def list_logs(limit=1000):
    """Fetch all system logs with hydrated actor details."""
    try:
        logs = SystemLog.objects.all().order_by('-log_id')[:limit]

        # 1. Collect unique identifiers for bulk fetching
        admin_users = set()
        staff_users = set()
        visitor_emails = set()

        for log in logs:
            identifier = _extract_identifier(log.actor)
            if log.actor_role == 'Admin':
                admin_users.add(identifier)
            elif log.actor_role == 'Staff':
                staff_users.add(identifier)
            elif log.actor_role == 'Visitor':
                visitor_emails.add(identifier)

        # 2. Bulk fetch actor real names to avoid N+1 queries
        # Map: username -> "First Last"
        admin_map = {
            a['username']: f"{a['first_name']} {a['last_name']}".strip() 
            for a in Administrator.objects.filter(username__in=admin_users).values('username', 'first_name', 'last_name')
        }
        
        staff_map = {
            s['username']: f"{s['first_name']} {s['last_name']}".strip() 
            for s in FrontDeskStaff.objects.filter(username__in=staff_users).values('username', 'first_name', 'last_name')
        }

        visitor_map = {
            v['email']: f"{v['first_name']} {v['last_name']}".strip() 
            for v in User.objects.filter(email__in=visitor_emails).values('email', 'first_name', 'last_name')
        }

        # 3. Build Result List
        result = []
        for log in logs:
            identifier = _extract_identifier(log.actor)
            display_name = log.actor # Default fallback

            # Try to find updated name from maps
            if log.actor_role == 'Admin':
                display_name = admin_map.get(identifier, log.actor.split(' (')[0])
            elif log.actor_role == 'Staff':
                display_name = staff_map.get(identifier, log.actor.split(' (')[0])
            elif log.actor_role == 'Visitor':
                display_name = visitor_map.get(identifier, log.actor.split(' (')[0])

            # Handle Timezone
            created_at = log.created_at or timezone.now()
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            result.append({
                'actor': display_name,
                'actor_email': identifier,
                'action_type': log.action_type,
                'description': log.description,
                'actor_role': log.actor_role,
                'created_at': created_at.isoformat()
            })
        
        return result

    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        return []

def create_log(actor, action_type, description, actor_role=""):
    """Create a new system log entry."""
    try:
        philippines_tz = pytz.timezone("Asia/Manila")
        current_time = datetime.now(philippines_tz)
        
        log = SystemLog(
            actor=actor,
            action_type=action_type,
            description=description,
            actor_role=actor_role,
            created_at=current_time,
        )
        log.save()
    except Exception as e:
        logger.error(f"Error creating log: {e}")

# ==============================
# REPORTS SERVICES
# ==============================

def list_visits(limit=2000):
    """
    Fetch visit data including related user info.
    Optimized with bulk fetching to prevent N+1 queries.
    """
    try:
        # Fetch visits
        visits = Visit.objects.all().order_by('-visit_date')[:limit]

        # Collect unique user emails for bulk fetching
        user_emails = set()
        for visit in visits:
            if visit.user_email:
                user_emails.add(visit.user_email)

        # Bulk fetch user names
        user_map = {
            u['email']: f"{u['first_name']} {u['last_name']}".strip()
            for u in User.objects.filter(email__in=user_emails).values('email', 'first_name', 'last_name')
        }

        data = []
        for visit in visits:
            # Get visitor name from map, fallback to Guest
            visitor_name = user_map.get(visit.user_email, "Guest")

            data.append({
                'visit_id': visit.visit_id,
                'user_id': visit.user_id,
                'visitor_name': visitor_name,  # Now real names
                'purpose': visit.purpose,
                'department': visit.department,
                'status': visit.status,
                'created_at': visit.created_at.isoformat() if visit.created_at else None,
                'visit_date': (visit.visit_date or visit.created_at.date()).isoformat() if visit.created_at else None,
                # UPDATED: Added Times for Hourly Chart
                'check_in_time': visit.start_time.strftime('%H:%M:%S') if visit.start_time else None,
                'check_out_time': visit.end_time.strftime('%H:%M:%S') if visit.end_time else None,
            })
        return data

    except Exception as e:
        logger.error(f"Error fetching visits: {e}")
        return []

def list_users(limit=2000):
    """Fetch visitor user data."""
    try:
        users = User.objects.all().order_by('created_at')[:limit]
        return [{
            'user_id': user.user_id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'visitor_type': user.visitor_type,
            'created_at': user.created_at.isoformat() if user.created_at else None
        } for user in users]
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return []

def list_staff(limit=1000):
    """Fetch staff data."""
    try:
        staff_members = FrontDeskStaff.objects.all().order_by('first_name')[:limit]
        return [{
            'staff_id': staff.staff_id,
            'first_name': staff.first_name,
            'last_name': staff.last_name,
            'created_at': staff.created_at.isoformat() if staff.created_at else None,
            'is_active': staff.is_active
        } for staff in staff_members]
    except Exception as e:
        logger.error(f"Error fetching staff: {e}")
        return []