from .models import SystemLog, AdminDismissedNotification
from django.utils import timezone

def visitor_notifications(request):
    # No user / not logged in → no notifications
    if not request.user.is_authenticated:
        return {}

    # You can adjust this logic to match whatever you use in the API
    visitor = request.user  # or request.user.visitor_profile, etc.

    notifications_qs = AdminDismissedNotification.objects.filter(
        user=visitor
    ).order_by("-created_at")[:20]

    notifications = []
    for n in notifications_qs:
        notifications.append({
            "title": n.title,
            "message": n.message,
            "time": timezone.localtime(n.created_at).strftime("%b %d, %Y %I:%M %p"),
        })

    return {
        "notifications": notifications
    }
