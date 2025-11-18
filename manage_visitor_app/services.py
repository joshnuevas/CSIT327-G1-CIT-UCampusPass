# manage_visitor_app/services.py
from register_app.models import User

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
                'created_at': visitor.created_at
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
                'created_at': visitor.created_at
            }]
        })()
    except User.DoesNotExist:
        return type('obj', (object,), {'data': []})()
    except Exception as e:
        print(f"Error fetching visitor: {e}")
        return type('obj', (object,), {'data': []})()