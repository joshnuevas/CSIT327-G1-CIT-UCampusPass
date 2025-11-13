"""
Visitor Search App Views
Handles visitor search and detailed visitor information
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import date, timedelta
import logging

# Setup
logger = logging.getLogger(__name__)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def staff_required(view_func):
    """Decorator to ensure only staff can access"""
    def wrapper(request, *args, **kwargs):
        if 'staff_username' not in request.session:
            messages.warning(request, "Please log in as staff to access this page.")
            return redirect('login_app:login')
        return view_func(request, *args, **kwargs)
    return wrapper


@staff_required
def visitor_search(request):
    """Search for visitors by name, email, phone, or code"""
    staff_first_name = request.session.get('staff_first_name', 'Staff')
    query = request.GET.get('query', '').strip()
    filter_type = request.GET.get('filter', 'all')
    
    results = []
    
    if query:
        try:
            # Search in visits table
            visits_resp = supabase.table("visits").select("*").execute()
            all_visits = visits_resp.data
            
            # Filter visits based on query
            matching_visits = []
            for visit in all_visits:
                email = visit.get('user_email', '').lower()
                code = visit.get('code', '').lower()
                purpose = visit.get('purpose', '').lower()
                department = visit.get('department', '').lower()
                
                if (query.lower() in email or 
                    query.lower() in code or
                    query.lower() in purpose or
                    query.lower() in department):
                    matching_visits.append(visit)
            
            # Apply filters
            today = date.today()
            if filter_type == 'active':
                matching_visits = [v for v in matching_visits if v.get('status') == 'Active']
            elif filter_type == 'today':
                today_str = today.strftime('%Y-%m-%d')
                matching_visits = [v for v in matching_visits if v.get('visit_date') == today_str]
            elif filter_type == 'week':
                week_start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
                matching_visits = [v for v in matching_visits if v.get('visit_date') >= week_start]
            
            # Group by visitor email
            visitors_dict = {}
            for visit in matching_visits:
                email = visit.get('user_email')
                if email not in visitors_dict:
                    visitors_dict[email] = {
                        'user_email': email,
                        'visitor_name': email.split('@')[0].title(),  # Simple name from email
                        'visits': [],
                        'current_visit': None,
                        'current_status': 'Completed',
                    }
                
                visitors_dict[email]['visits'].append(visit)
                
                # Set current visit (Active or most recent Upcoming)
                if visit.get('status') in ['Active', 'Upcoming']:
                    if not visitors_dict[email]['current_visit']:
                        visitors_dict[email]['current_visit'] = visit
                        visitors_dict[email]['current_status'] = visit.get('status')
                    elif visit.get('status') == 'Active':
                        visitors_dict[email]['current_visit'] = visit
                        visitors_dict[email]['current_status'] = 'Active'
            
            # Prepare results
            for email, visitor_data in visitors_dict.items():
                # Sort visits by date descending
                visitor_data['visits'].sort(key=lambda x: x.get('visit_date', ''), reverse=True)
                visitor_data['visit_history'] = visitor_data['visits'][:10]  # Last 10 visits
                visitor_data['total_visits'] = len(visitor_data['visits'])
                results.append(visitor_data)
            
            # Sort results by current status (Active first, then Upcoming, then others)
            status_priority = {'Active': 0, 'Upcoming': 1, 'Completed': 2, 'Expired': 3}
            results.sort(key=lambda x: status_priority.get(x['current_status'], 9))
            
        except Exception as e:
            logger.error(f"Error in visitor search: {str(e)}")
            messages.error(request, "An error occurred during search.")
    
    context = {
        'staff_first_name': staff_first_name,
        'query': query,
        'filter': filter_type,
        'results': results,
    }
    
    return render(request, 'visitor_search_app/visitor_search.html', context)


@staff_required
def visitor_detail(request):
    """Show detailed information about a specific visitor"""
    staff_first_name = request.session.get('staff_first_name', 'Staff')
    visitor_email = request.GET.get('email', '').strip()
    
    if not visitor_email:
        messages.error(request, "Visitor email is required.")
        return redirect('visitor_search_app:search')
    
    try:
        # Get all visits for this visitor
        visits_resp = supabase.table("visits").select("*").eq("user_email", visitor_email).execute()
        visits = visits_resp.data
        
        if not visits:
            messages.error(request, "No visits found for this visitor.")
            return redirect('visitor_search_app:search')
        
        # Sort visits by date descending
        visits.sort(key=lambda x: x.get('visit_date', ''), reverse=True)
        
        # Get visitor name (simple extraction from email)
        visitor_name = visitor_email.split('@')[0].title()
        
        # Calculate statistics
        total_visits = len(visits)
        completed_visits = len([v for v in visits if v.get('status') == 'Completed'])
        current_visit = next((v for v in visits if v.get('status') in ['Active', 'Upcoming']), None)
        last_visit_date = visits[0].get('visit_date') if visits else None
        
        context = {
            'staff_first_name': staff_first_name,
            'visitor_email': visitor_email,
            'visitor_name': visitor_name,
            'total_visits': total_visits,
            'completed_visits': completed_visits,
            'current_visit': current_visit,
            'last_visit_date': last_visit_date,
            'visit_history': visits,
        }
        
        return render(request, 'visitor_search_app/visitor_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error loading visitor detail: {str(e)}")
        messages.error(request, "An error occurred loading visitor details.")
        return redirect('visitor_search_app:search')