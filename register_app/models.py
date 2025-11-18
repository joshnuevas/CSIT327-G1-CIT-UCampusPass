# models.py (put this in your appropriate app)
from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class User(models.Model):
    VISITOR_TYPE_CHOICES = [
        ('Parent', 'Parent'),
        ('Student', 'Student'),
        ('Alumni', 'Alumni'),
        ('Guest', 'Guest'),
        ('Vendor', 'Vendor'),
        ('Other', 'Other'),
    ]
    
    user_id = models.BigAutoField(primary_key=True)  
    first_name = models.TextField()  
    last_name = models.TextField()   
    email = models.TextField()       
    phone = models.TextField()       
    password = models.TextField()    
    created_at = models.DateTimeField(auto_now_add=True)
    visitor_type = models.TextField()
    
    class Meta:
        db_table = 'users'  # Use your existing table name
    
    def set_password(self, raw_password):
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"