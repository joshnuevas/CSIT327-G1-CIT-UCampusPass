# manage_staff_app/services.py
from login_app.models import FrontDeskStaff

def list_staff(limit=100, offset=0):
    try:
        staff = FrontDeskStaff.objects.all().order_by('username')[offset:offset+limit]
        # Convert to list of dictionaries for compatibility
        return type('obj', (object,), {
            'data': [{
                'staff_id': staff_member.staff_id,
                'username': staff_member.username,
                'first_name': staff_member.first_name,
                'last_name': staff_member.last_name,
                'email': getattr(staff_member, 'email', ''),
                'contact_number': getattr(staff_member, 'contact_number', ''),
                'is_active': staff_member.is_active,
                'is_temp_password': staff_member.is_temp_password,
                'created_at': None  # This field doesn't exist in your model
            } for staff_member in staff]
        })()
    except Exception as e:
        print(f"Error listing staff: {e}")
        return type('obj', (object,), {'data': []})()

def get_staff_by_username(username):
    try:
        staff_member = FrontDeskStaff.objects.get(username=username)
        return type('obj', (object,), {
            'data': [{
                'staff_id': staff_member.staff_id,
                'username': staff_member.username,
                'first_name': staff_member.first_name,
                'last_name': staff_member.last_name,
                'email': getattr(staff_member, 'email', ''),
                'contact_number': getattr(staff_member, 'contact_number', ''),
                'is_active': staff_member.is_active,
                'is_temp_password': staff_member.is_temp_password,
                'created_at': None  # This field doesn't exist in your model
            }]
        })()
    except FrontDeskStaff.DoesNotExist:
        return type('obj', (object,), {'data': []})()
    except Exception as e:
        print(f"Error getting staff by username: {e}")
        return type('obj', (object,), {'data': []})()

def create_staff(record: dict):
    try:
        staff_member = FrontDeskStaff(
            username=record['username'],
            first_name=record['first_name'],
            last_name=record.get('last_name', ''),
            email=record.get('email', ''),
            contact_number=record.get('contact_number', ''),
            password=record['password'],
            is_temp_password=record.get('is_temp_password', True),
            is_active=record.get('is_active', True)
        )
        staff_member.save()
        return type('obj', (object,), {'data': [{'staff_id': staff_member.staff_id}], 'status_code': 201})()
    except Exception as e:
        print(f"Error creating staff: {e}")
        return type('obj', (object,), {'data': [], 'status_code': 500})()

def update_staff(username, updates: dict):
    try:
        staff_member = FrontDeskStaff.objects.get(username=username)
        for key, value in updates.items():
            setattr(staff_member, key, value)
        staff_member.save()
        return type('obj', (object,), {'data': [{'updated': True}], 'status_code': 200})()
    except FrontDeskStaff.DoesNotExist:
        return type('obj', (object,), {'data': [], 'status_code': 404})()
    except Exception as e:
        print(f"Error updating staff: {e}")
        return type('obj', (object,), {'data': [], 'status_code': 500})()

def deactivate_staff(username):
    try:
        staff_member = FrontDeskStaff.objects.get(username=username)
        staff_member.is_active = False
        staff_member.save()
        return type('obj', (object,), {'data': [{'deactivated': True}], 'status_code': 200})()
    except FrontDeskStaff.DoesNotExist:
        return type('obj', (object,), {'data': [], 'status_code': 404})()
    except Exception as e:
        print(f"Error deactivating staff: {e}")
        return type('obj', (object,), {'data': [], 'status_code': 500})()

def delete_staff(username):
    try:
        staff_member = FrontDeskStaff.objects.get(username=username)
        staff_member.delete()
        return type('obj', (object,), {'data': [{'deleted': True}], 'status_code': 200})()
    except FrontDeskStaff.DoesNotExist:
        return type('obj', (object,), {'data': [], 'status_code': 404})()
    except Exception as e:
        print(f"Error deleting staff: {e}")
        return type('obj', (object,), {'data': [], 'status_code': 500})()