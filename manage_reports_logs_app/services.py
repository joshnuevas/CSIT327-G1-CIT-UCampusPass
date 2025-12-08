# manage_reports_logs_app/services.py
from django.conf import settings
from datetime import datetime

# Import Django models
from dashboard_app.models import SystemLog, Visit
from register_app.models import User
from login_app.models import Administrator, FrontDeskStaff

# ==============================
# LOGS SERVICES
# ==============================
def list_logs(limit=1000):
    """Fetch all system logs."""
    from django.utils import timezone
    try:
        logs = SystemLog.objects.all().order_by('-log_id')[:limit]

        # Collect unique actors by role for bulk queries
        admin_usernames = set()
        staff_usernames = set()
        visitor_emails = set()

        for log in logs:
            if log.actor_role == 'Admin':
                # Extract username from "first_name (username)"
                if '(' in log.actor and log.actor.endswith(')'):
                    username = log.actor.split('(')[-1].rstrip(')')
                else:
                    username = log.actor
                admin_usernames.add(username)
            elif log.actor_role == 'Staff':
                # Extract username from "first_name (username)"
                if '(' in log.actor and log.actor.endswith(')'):
                    username = log.actor.split('(')[-1].rstrip(')')
                else:
                    username = log.actor
                staff_usernames.add(username)
            elif log.actor_role == 'Visitor':
                # Extract email from "first_name last_name (email)"
                if '(' in log.actor and log.actor.endswith(')'):
                    email = log.actor.split('(')[-1].rstrip(')')
                else:
                    email = log.actor
                visitor_emails.add(email)

        # Bulk fetch actor details
        admin_dict = {}
        if admin_usernames:
            admins = Administrator.objects.filter(username__in=admin_usernames).values('username', 'first_name', 'last_name')
            for admin in admins:
                admin_dict[admin['username']] = f"{admin['first_name']} {admin['last_name']}".strip()

        staff_dict = {}
        if staff_usernames:
            staffs = FrontDeskStaff.objects.filter(username__in=staff_usernames).values('username', 'first_name', 'last_name')
            for staff in staffs:
                staff_dict[staff['username']] = f"{staff['first_name']} {staff['last_name']}".strip()

        visitor_dict = {}
        if visitor_emails:
            visitors = User.objects.filter(email__in=visitor_emails).values('email', 'first_name', 'last_name')
            for visitor in visitors:
                visitor_dict[visitor['email']] = f"{visitor['first_name']} {visitor['last_name']}".strip()

        # Convert to list of dictionaries for JSON serialization
        result = []
        for log in logs:
            created_at = log.created_at
            if not created_at:
                created_at = timezone.now()
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            created_at_str = created_at.isoformat()

            # Get actor name from bulk fetched data
            if log.actor_role == 'Admin':
                # Extract username
                if '(' in log.actor and log.actor.endswith(')'):
                    username = log.actor.split('(')[-1].rstrip(')')
                else:
                    username = log.actor
                actor_name = admin_dict.get(username, log.actor.split(' (')[0] if ' (' in log.actor else log.actor)
                actor_sub = username
            elif log.actor_role == 'Staff':
                # Extract username
                if '(' in log.actor and log.actor.endswith(')'):
                    username = log.actor.split('(')[-1].rstrip(')')
                else:
                    username = log.actor
                actor_name = staff_dict.get(username, log.actor.split(' (')[0] if ' (' in log.actor else log.actor)
                actor_sub = username
            elif log.actor_role == 'Visitor':
                # Extract email
                if '(' in log.actor and log.actor.endswith(')'):
                    email = log.actor.split('(')[-1].rstrip(')')
                else:
                    email = log.actor
                actor_name = visitor_dict.get(email, log.actor.split(' (')[0] if ' (' in log.actor else log.actor)
                actor_sub = email
            else:
                actor_name = log.actor
                actor_sub = log.actor

            result.append({
                'actor': actor_name,
                'actor_email': actor_sub,
                'action_type': log.action_type,
                'description': log.description,
                'actor_role': log.actor_role,
                'created_at': created_at_str
            })
        return result
    except Exception as e:
        print("Error fetching logs:", e)
        return []

def create_log(actor, action_type, description, actor_role=""):
    """Create a new system log entry."""
    from datetime import datetime
    import pytz
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
        print("Error creating log:", e)

# ==============================
# REPORTS SERVICES
# ==============================
def list_visits(limit=2000):
    """Fetch visit data."""
    try:
        visits = Visit.objects.all().order_by('-visit_date')[:limit]
        # Convert to list of dictionaries for JSON serialization
        return [{
            'visit_id': visit.visit_id,
            'user_id': visit.user_id,
            'purpose': visit.purpose,
            'department': visit.department,
            'status': visit.status,
            'created_at': visit.created_at,
            'visit_date': visit.visit_date
        } for visit in visits]
    except Exception as e:
        print("Error fetching visits:", e)
        return []

def list_users(limit=2000):
    """Fetch visitor data."""
    try:
        users = User.objects.all().order_by('created_at')[:limit]
        # Convert to list of dictionaries for JSON serialization
        # FIXED: Changed 'visit' to 'user' in the list comprehension
        return [{
            'user_id': user.user_id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'visitor_type': user.visitor_type,
            'created_at': user.created_at
        } for user in users]  # ← FIXED: Changed 'visit' to 'user'
    except Exception as e:
        print("Error fetching users:", e)
        return []

def list_staff(limit=1000):
    """Fetch staff data for charts and filters."""
    try:
        staff = FrontDeskStaff.objects.all().order_by('first_name')[:limit]
        # Convert to list of dictionaries for JSON serialization
        return [{
            'staff_id': staff_member.staff_id,
            'first_name': staff_member.first_name,
            'last_name': staff_member.last_name,
            'created_at': staff_member.created_at,
            'is_active': staff_member.is_active
        } for staff_member in staff]
    except Exception as e:
        print("Error fetching staff:", e)
        return []