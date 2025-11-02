from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from supabase import create_client
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables and create Supabase client
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def help_support_view(request):
    """Display help and support page with FAQs and contact form."""
    
    # Check if user is logged in to get their info
    user_email = request.session.get('user_email', '')
    user_first_name = request.session.get('user_first_name', '')
    
    # Get user_id (bigint) if logged in
    user_id = None
    if user_email:
        try:
            user_resp = supabase.table("users").select("user_id").eq("email", user_email).execute()
            if user_resp.data:
                user_id = user_resp.data[0]['user_id']  # This is already a bigint
        except Exception as e:
            logger.error(f"Error fetching user_id: {str(e)}")
    
    if request.method == 'POST':
        # Handle contact form submission
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        form_type = request.POST.get('form_type', '')
        
        # Validate fields
        if not all([name, email, message]):
            messages.error(request, "Please fill in all required fields.")
            return redirect('help_support')
        
        # Validate form_type
        if form_type not in ['feedback', 'support']:
            form_type = 'support'  # Default to support if invalid
        
        # Determine email content
        if form_type == 'feedback':
            email_subject = f"CIT-U CampusPass | Feedback from {name}"
            email_message = (
                f"New Feedback Received\n\n"
                f"From: {name}\n"
                f"Email: {email}\n\n"
                f"Message:\n{message}\n\n"
                f"---\n"
                f"Sent via CIT-U CampusPass Help & Support"
            )
            success_msg = "Thank you for your feedback! We appreciate your input."
        else:
            email_subject = f"CIT-U CampusPass | Support Request: {subject}"
            email_message = (
                f"New Support Request\n\n"
                f"From: {name}\n"
                f"Email: {email}\n"
                f"Subject: {subject}\n\n"
                f"Message:\n{message}\n\n"
                f"---\n"
                f"Sent via CIT-U CampusPass Help & Support"
            )
            success_msg = "Your message has been sent! We'll get back to you soon."
        
        # Save to Supabase help_messages table
        saved_to_db = False
        try:
            data_to_insert = {
                'name': name,
                'email': email,
                'message': message,
                'form_type': form_type
            }
            
            # Add user_id if logged in
            if user_id:
                data_to_insert['user_id'] = user_id
            
            # Add subject for support requests (can be null for feedback)
            if form_type == 'support' and subject:
                data_to_insert['subject'] = subject
            
            supabase.table('help_messages').insert(data_to_insert).execute()
            saved_to_db = True
            logger.info(f"{form_type} message saved to database from {name} ({email})")
        except Exception as e:
            logger.error(f"Failed to save message to database: {str(e)}")
            messages.error(request, "Failed to save your message. Please try again.")
            return redirect('help_support')
        
        # Try to send email notification (optional)
        email_sent = False
        if saved_to_db and settings.EMAIL_HOST_USER:
            try:
                send_mail(
                    email_subject,
                    email_message,
                    settings.DEFAULT_FROM_EMAIL,
                    ['citucampuspass@gmail.com'],
                    fail_silently=False,
                    timeout=10
                )
                email_sent = True
                logger.info(f"Email notification sent for {form_type} from {email}")
            except Exception as e:
                logger.error(f"Failed to send email notification: {str(e)}")
        
        # Show appropriate success message
        if saved_to_db:
            messages.success(request, success_msg)
            if not email_sent and settings.EMAIL_HOST_USER:
                messages.info(request, "Note: Email notification failed, but your message was saved.")
        
        return redirect('help_support')
    
    # GET request - render the page
    context = {
        'user_email': user_email,
        'user_first_name': user_first_name,
    }
    return render(request, 'help_app/help_support.html', context)