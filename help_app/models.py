from django.db import models

class HelpMessage(models.Model):
    help_id = models.BigAutoField(primary_key=True)  # Matches your help_id bigint
    user_id = models.BigIntegerField(null=True, blank=True)  # Matches your user_id bigint
    name = models.TextField()
    email = models.TextField()
    subject = models.TextField(null=True, blank=True)
    message = models.TextField()
    form_type = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)  # Django will handle timestamps
    
    class Meta:
        db_table = 'help_messages'
        managed = False