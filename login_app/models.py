from django.db import models
from django.contrib.auth.hashers import make_password, check_password

from register_app.models import User

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