# help_app/views.py
from django.shortcuts import render
import logging

from register_app.models import User

logger = logging.getLogger(__name__)

def help_support_view(request):
    """Display help and support page with FAQs and troubleshooting only."""
    
    # Check if user is logged in to get their info (optional, in case you reuse later)
    user_email = request.session.get('user_email', '')
    user_first_name = request.session.get('user_first_name', '')
    
    # Optionally verify user exists (not strictly needed if you're not saving anything)
    if user_email:
        try:
            User.objects.get(email=user_email)
        except User.DoesNotExist:
            logger.error(f"User not found with email: {user_email}")
        except Exception as e:
            logger.error(f"Error fetching user: {str(e)}")
    
    context = {
        'user_email': user_email,
        'user_first_name': user_first_name,
    }
    return render(request, 'help_app/help_support.html', context)
