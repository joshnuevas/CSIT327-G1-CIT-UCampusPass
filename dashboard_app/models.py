from django.db import models

class Visit(models.Model):
    visit_id = models.BigAutoField(primary_key=True)
    user_email = models.TextField()
    code = models.TextField(unique=True)
    purpose = models.TextField()
    department = models.TextField()
    visit_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    status = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    user_id = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'visits'
        managed = False

class SystemLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    actor = models.TextField()
    action_type = models.TextField()
    description = models.TextField()
    actor_role = models.TextField()
    created_at = models.DateTimeField()
    
    class Meta:
        db_table = 'system_logs'
        managed = False

class AdminDismissedNotification(models.Model):
    admin_username = models.TextField()
    log_id = models.BigIntegerField()
    
    class Meta:
        db_table = 'admin_dismissed_notifications'
        managed = False

# Import other models
from login_app.models import Administrator, FrontDeskStaff
from register_app.models import User