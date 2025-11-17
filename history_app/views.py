from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def history_view(request):
    # Redirect if not logged in
    if 'user_email' not in request.session:
        return redirect('login_app:login')

    user_email = request.session['user_email']
    visits_resp = supabase.table("visits").select("*").eq("user_email", user_email).execute()
    visits = visits_resp.data

    # Format visit dates and times like in dashboard
    from datetime import datetime, date
    today = date.today()
    for visit in visits:
        visit_date_obj = datetime.strptime(visit['visit_date'], "%Y-%m-%d").date()
        visit['display_date'] = f"Today, {visit_date_obj.strftime('%b %d')}" if visit_date_obj == today else visit_date_obj.strftime("%b %d, %Y")
        
        # Format start time - handle null start_time
        if visit['start_time']:
            visit['formatted_start_time'] = datetime.strptime(visit['start_time'], "%H:%M:%S").strftime("%I:%M %p")
        else:
            visit['formatted_start_time'] = "Not checked in"
        
        # Format end time ONLY if it exists (not None)
        if visit['end_time']:
            visit['formatted_end_time'] = datetime.strptime(visit['end_time'], "%H:%M:%S").strftime("%I:%M %p")
        else:
            visit['formatted_end_time'] = "Pending"

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
        visit_check = supabase.table("visits").select("*").eq("visit_id", visit_id).execute()
        print(f"Visit check result: {visit_check.data}")
        
        if not visit_check.data:
            print("Visit not found in database")
            messages.error(request, 'Visit not found.')
            return redirect('history_app:visit_history')
        
        visit_data = visit_check.data[0]
        
        if visit_data['user_email'] != user_email:
            print("User does not own this visit")
            messages.error(request, 'You do not have permission to cancel this visit.')
            return redirect('history_app:visit_history')
        
        # Store visit details for logging before deletion
        visit_code = visit_data.get('code', 'N/A')
        visit_date = visit_data.get('visit_date', 'N/A')
        department = visit_data.get('department', 'N/A')
        
        # Delete the visit from the database
        delete_result = supabase.table("visits").delete().eq("visit_id", visit_id).execute()
        print(f"Delete result: {delete_result}")
        
        # Create log entry for the cancellation
        from datetime import datetime
        import pytz
        
        # Use Philippines timezone
        philippines_tz = pytz.timezone('Asia/Manila')
        current_time = datetime.now(philippines_tz)
        
        log_entry = {
            "actor": user_email,
            "action_type": "Visit Cancelled",
            "description": f"User cancelled visit {visit_code} scheduled for {visit_date} at {department}",
            "actor_role": "Visitor",
            "created_at": current_time.isoformat()
        }
        supabase.table("system_logs").insert(log_entry).execute()
        print(f"Log entry created for cancelled visit: {visit_code}")
        
        messages.success(request, 'Visit cancelled successfully.')
        print("Visit deleted successfully")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        messages.error(request, f'An error occurred while cancelling the visit: {str(e)}')
    
    return redirect('history_app:visit_history')