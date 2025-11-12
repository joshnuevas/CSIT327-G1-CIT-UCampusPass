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
        visit['formatted_start_time'] = datetime.strptime(visit['start_time'], "%H:%M:%S").strftime("%I:%M %p")
        visit['formatted_end_time'] = datetime.strptime(visit['end_time'], "%H:%M:%S").strftime("%I:%M %p")

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
        visit_check = supabase.table("visits").select("user_email").eq("visit_id", visit_id).execute()
        print(f"Visit check result: {visit_check.data}")
        
        if not visit_check.data:
            print("Visit not found in database")
            messages.error(request, 'Visit not found.')
            return redirect('history_app:visit_history')
        
        if visit_check.data[0]['user_email'] != user_email:
            print("User does not own this visit")
            messages.error(request, 'You do not have permission to cancel this visit.')
            return redirect('history_app:visit_history')
        
        # Delete the visit from the database
        delete_result = supabase.table("visits").delete().eq("visit_id", visit_id).execute()
        print(f"Delete result: {delete_result}")
        messages.success(request, 'Visit cancelled successfully.')
        print("Visit deleted successfully")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        messages.error(request, f'An error occurred while cancelling the visit: {str(e)}')
    
    return redirect('history_app:visit_history')