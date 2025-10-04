from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    phone = models.CharField(max_length=15, blank=True)

class Visit(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    title = models.CharField(max_length=100)
    date_start = models.DateTimeField()
    date_end = models.DateTimeField()
    status_choices = [
        ('Active', 'Active'),
        ('Upcoming', 'Upcoming'),
        ('Expired', 'Expired'),
    ]
    status = models.CharField(max_length=10, choices=status_choices, default='Upcoming')

    def __str__(self):
        return f"{self.code} - {self.user.username}"