from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from datetime import datetime, date
import pytz

# Import Django models
from dashboard_app.models import Visit, SystemLog
from register_app.models import User

def history_view(request):
    # Redirect if not logged in
    if 'user_email' not in request.session:
        return redirect('login_app:login')

    user_email = request.session['user_email']
    
    # Use Django ORM instead of Supabase
    visits = Visit.objects.filter(user_email=user_email)

    # Format visit dates and times like in dashboard
    today = date.today()
    for visit in visits:
        visit_date_obj = visit.visit_date
        visit.display_date = f"Today, {visit_date_obj.strftime('%b %d')}" if visit_date_obj == today else visit_date_obj.strftime("%b %d, %Y")
        
        # Format start time - handle null start_time
        if visit.start_time:
            visit.formatted_start_time = visit.start_time.strftime("%I:%M %p")
        else:
            visit.formatted_start_time = "Not checked in"
        
        # Format end time ONLY if it exists (not None)
        if visit.end_time:
            visit.formatted_end_time = visit.end_time.strftime("%I:%M %p")
        else:
            visit.formatted_end_time = "Pending"

    context = {
        "user_email": user_email,
        "user_first_name": request.session.get('user_first_name'),
        "visits": visits,
    }
    return render(request, 'history_app/history.html', context)

@require_POST
def cancel_visit(request):
    print("=== Cancel Visit Function Called ===")
    
    # Check if user is logged in
    if 'user_email' not in request.session:
        print("User not logged in")
        return redirect('login_app:login')
    
    visit_id = request.POST.get('visit_id')
    user_email = request.session['user_email']
    
    print(f"Visit ID: {visit_id}")
    print(f"User Email: {user_email}")
    
    if not visit_id:
        print("No visit ID provided")
        messages.error(request, 'Invalid visit ID.')
        return redirect('history_app:visit_history')
    
    try:
        # Verify the visit belongs to the current user before deleting
        try:
            visit = Visit.objects.get(visit_id=visit_id)
            print(f"Visit found: {visit.code}")
        except Visit.DoesNotExist:
            print("Visit not found in database")
            messages.error(request, 'Visit not found.')
            return redirect('history_app:visit_history')
        
        if visit.user_email != user_email:
            print("User does not own this visit")
            messages.error(request, 'You do not have permission to cancel this visit.')
            return redirect('history_app:visit_history')
        
        # Store visit details for logging before deletion
        visit_code = visit.code or 'N/A'
        visit_date = visit.visit_date or 'N/A'
        department = visit.department or 'N/A'
        
        # Delete the visit from the database using Django ORM
        visit.delete()
        print(f"Visit deleted: {visit_code}")
        
        # Create log entry for the cancellation
        # Use Philippines timezone
        philippines_tz = pytz.timezone('Asia/Manila')
        current_time = datetime.now(philippines_tz)
        
        log_entry = SystemLog(
            actor=user_email,
            action_type="Visit Cancelled",
            description=f"User cancelled visit {visit_code} scheduled for {visit_date} at {department}",
            actor_role="Visitor",
            created_at=current_time
        )
        log_entry.save()
        print(f"Log entry created for cancelled visit: {visit_code}")
        
        messages.success(request, 'Visit cancelled successfully.')
        print("Visit deleted successfully")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        messages.error(request, f'An error occurred while cancelling the visit: {str(e)}')
    
    return redirect('history_app:visit_history')