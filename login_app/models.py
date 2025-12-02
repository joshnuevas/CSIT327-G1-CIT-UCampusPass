from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

from register_app.models import User
import uuid


class Administrator(models.Model):
    admin_id = models.BigAutoField(primary_key=True)
    first_name = models.TextField()
    last_name = models.TextField()
    username = models.TextField(unique=True)
    email = models.TextField()
    password = models.TextField()
    contact_number = models.TextField()
    is_superadmin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_temp_password = models.BooleanField(default=False)

    class Meta:
        db_table = 'administrator'
        managed = False

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


class FrontDeskStaff(models.Model):
    staff_id = models.BigAutoField(primary_key=True)
    first_name = models.TextField()
    last_name = models.TextField()
    username = models.TextField(unique=True)
    email = models.TextField()
    password = models.TextField()
    contact_number = models.TextField()
    is_temp_password = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'front_desk_staff'
        managed = False

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


class PasswordResetToken(models.Model):
    """
    Password reset tokens for VISITOR users (register_app.User).
    Admin/staff you already handle with temp passwords.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    token = models.CharField(
        max_length=100,
        unique=True,
        default=uuid.uuid4
    )
    created_at = models.DateTimeField(default=timezone.now)

    def is_expired(self):
        # Token valid for 1 hour (adjust if needed)
        return self.created_at < timezone.now() - timezone.timedelta(hours=1)

    def __str__(self):
        return f"Password reset token for {self.user.email}"
