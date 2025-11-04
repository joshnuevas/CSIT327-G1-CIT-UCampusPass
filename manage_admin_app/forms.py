# manage_admin_app/forms.py
from django import forms

class AdminCreateForm(forms.Form):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField(required=True)
    contact_number = forms.CharField(max_length=20, required=False)

class AdminEditForm(forms.Form):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField(required=True)
    contact_number = forms.CharField(max_length=20, required=False)
    is_active = forms.BooleanField(required=False)
