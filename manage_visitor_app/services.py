# manage_visitor_app/services.py
from register_app.models import User
from dashboard_app.models import Visit

def list_visitors(limit=500):
    """
    Fetch only visitors from the 'users' table.
    We assume visitor_type is set for visitors (e.g., 'guest', 'parent', 'student', etc.)
    """
    try:
        visitors = User.objects.exclude(visitor_type__isnull=True).order_by('user_id')[:limit]
        # Convert to list of dictionaries for compatibility with existing views
        return type('obj', (object,), {
            'data': [{
                'user_id': visitor.user_id,
                'first_name': visitor.first_name,
                'last_name': visitor.last_name,
                'email': visitor.email,
                'phone': visitor.phone,
                'visitor_type': visitor.visitor_type,
                'created_at': visitor.created_at,
                'is_active': getattr(visitor, 'is_active', True)
            } for visitor in visitors]
        })()
    except Exception as e:
        print(f"Error fetching visitors: {e}")
        return type('obj', (object,), {'data': []})()

def deactivate_visitor(user_id):
    """Deactivate visitor by deleting them from the database"""
    try:
        user = User.objects.get(user_id=user_id)
        user.delete()
        return type('obj', (object,), {'data': [{'deleted': True}]})()
    except User.DoesNotExist:
        return type('obj', (object,), {'data': []})()
    except Exception as e:
        print(f"Error deleting visitor: {e}")
        return type('obj', (object,), {'data': []})()

def get_visitor_by_id(user_id):
    """Fetch a single visitor by user_id"""
    try:
        visitor = User.objects.get(user_id=user_id)
        return type('obj', (object,), {
            'data': [{
                'user_id': visitor.user_id,
                'first_name': visitor.first_name,
                'last_name': visitor.last_name,
                'email': visitor.email,
                'phone': visitor.phone,
                'visitor_type': visitor.visitor_type,
                'created_at': visitor.created_at,
                'is_active': getattr(visitor, 'is_active', True)
            }]
        })()
    except User.DoesNotExist:
        return type('obj', (object,), {'data': []})()
    except Exception as e:
        print(f"Error fetching visitor: {e}")
        return type('obj', (object,), {'data': []})()

def get_visitor_history(user_id):
    """
    Fetch all visits for a specific user, ordered by date descending.
    """
    try:
        # Fetch visits filtering by the user_id
        # Using the Visit model imported from dashboard_app.models
        visits = Visit.objects.filter(user_id=user_id).order_by('-visit_date')
        
        return type('obj', (object,), {
            'data': [{
                'visit_date': v.visit_date,
                'code': v.code,
                'department': v.department,
                'status': v.status,
                'purpose': v.purpose,
                'start_time': v.start_time, # Optional: helpful for detail view
                'end_time': v.end_time,     # Optional: helpful for detail view
            } for v in visits]
        })()
    except Exception as e:
        print(f"Error fetching history for {user_id}: {e}")
        return type('obj', (object,), {'data': []})()