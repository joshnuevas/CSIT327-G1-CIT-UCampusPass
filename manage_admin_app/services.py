# manage_admin_app/services.py
from login_app.models import Administrator

def list_admins(limit: int = 500):
    try:
        admins = Administrator.objects.all().order_by('created_at')[:limit]
        # Convert to list of dictionaries for compatibility
        return type('obj', (object,), {
            'data': [{
                'admin_id': admin.admin_id,
                'username': admin.username,
                'first_name': admin.first_name,
                'last_name': admin.last_name,
                'email': admin.email,
                'contact_number': admin.contact_number,
                'is_superadmin': admin.is_superadmin,
                'is_active': admin.is_active,
                'is_temp_password': admin.is_temp_password,
                'created_at': admin.created_at
            } for admin in admins]
        })()
    except Exception as e:
        print(f"Error listing admins: {e}")
        return type('obj', (object,), {'data': []})()

def get_admin_by_username(username: str):
    try:
        admin = Administrator.objects.get(username=username)
        return type('obj', (object,), {
            'data': [{
                'admin_id': admin.admin_id,
                'username': admin.username,
                'first_name': admin.first_name,
                'last_name': admin.last_name,
                'email': admin.email,
                'contact_number': admin.contact_number,
                'is_superadmin': admin.is_superadmin,
                'is_active': admin.is_active,
                'is_temp_password': admin.is_temp_password,
                'created_at': admin.created_at
            }]
        })()
    except Administrator.DoesNotExist:
        return type('obj', (object,), {'data': []})()
    except Exception as e:
        print(f"Error getting admin by username: {e}")
        return type('obj', (object,), {'data': []})()

def create_admin(data: dict):
    try:
        admin = Administrator(
            username=data['username'],
            first_name=data['first_name'],
            last_name=data.get('last_name', ''),
            email=data.get('email', ''),
            contact_number=data.get('contact_number', ''),
            password=data['password'],
            is_superadmin=data.get('is_superadmin', False),
            is_active=data.get('is_active', True),
            is_temp_password=data.get('is_temp_password', True)
        )
        admin.save()
        # Return the created admin data
        return get_admin_by_username(data['username'])
    except Exception as e:
        print(f"Error creating admin: {e}")
        return type('obj', (object,), {'data': []})()

def update_admin(username: str, updates: dict):
    try:
        admin = Administrator.objects.get(username=username)
        allowed_fields = ["first_name", "last_name", "email", "contact_number",
                         "password", "is_temp_password", "is_active"]
        clean_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        for key, value in clean_updates.items():
            setattr(admin, key, value)
        admin.save()
        
        # Return the updated admin data
        return get_admin_by_username(username)
    except Administrator.DoesNotExist:
        return type('obj', (object,), {'data': []})()
    except Exception as e:
        print(f"Error updating admin: {e}")
        return type('obj', (object,), {'data': []})()

def deactivate_admin(username: str):
    try:
        admin = Administrator.objects.get(username=username)
        admin.is_active = False
        admin.save()
        return get_admin_by_username(username)
    except Administrator.DoesNotExist:
        return type('obj', (object,), {'data': []})()
    except Exception as e:
        print(f"Error deactivating admin: {e}")
        return type('obj', (object,), {'data': []})()

def activate_admin(username: str):
    try:
        admin = Administrator.objects.get(username=username)
        admin.is_active = True
        admin.save()
        return get_admin_by_username(username)
    except Administrator.DoesNotExist:
        return type('obj', (object,), {'data': []})()
    except Exception as e:
        print(f"Error activating admin: {e}")
        return type('obj', (object,), {'data': []})()

def reset_admin_password(username: str, temp_password: str):
    try:
        admin = Administrator.objects.get(username=username)
        admin.set_password(temp_password)
        admin.is_temp_password = True
        admin.save()
        return get_admin_by_username(username)
    except Administrator.DoesNotExist:
        return type('obj', (object,), {'data': []})()
    except Exception as e:
        print(f"Error resetting admin password: {e}")
        return type('obj', (object,), {'data': []})()