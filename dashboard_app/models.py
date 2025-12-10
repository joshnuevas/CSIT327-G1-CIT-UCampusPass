from django.db import models
from login_app.models import Administrator, FrontDeskStaff
from register_app.models import User


class Notification(models.Model):
    notification_id = models.BigAutoField(primary_key=True)

    # Receivers
    receiver_admin = models.ForeignKey(
        Administrator,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        db_column='receiver_admin_id'
    )
    receiver_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        db_column='receiver_user_id'
    )

    # Senders (optional)
    sender_admin = models.ForeignKey(
        Administrator,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='sender_admin_id',
        related_name='sent_admin_notifications'
    )
    sender_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='sender_user_id',
        related_name='sent_user_notifications'
    )

    # Core notification content
    type = models.TextField()       # e.g. "visitor_arrived", "system_alert"
    title = models.TextField()
    message = models.TextField()

    # Link to visit (optional)
    visit = models.ForeignKey(
        'Visit',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        db_column='visit_id'
    )

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        managed = False


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
