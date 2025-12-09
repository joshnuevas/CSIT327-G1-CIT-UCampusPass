# manage_staff_app/forms.py
from django import forms

class StaffCreateForm(forms.Form):
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'input-modern', 'placeholder': 'Enter first name'}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'input-modern', 'placeholder': 'Enter last name'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'input-modern', 'placeholder': 'your@email.com', 'pattern': '^[^@\s]+@[^@\s]+\.[^@\s]{2,}$', 'oninvalid': "this.setCustomValidity('Please enter a valid email address (e.g., name@example.com).')", 'oninput': "this.setCustomValidity('')"}))
    contact_number = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'input-modern', 'placeholder': '09123456789', 'pattern': '^09\d{9}$', 'minlength': '11', 'maxlength': '11', 'inputmode': 'numeric'}))

class StaffEditForm(forms.Form):
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'input-modern', 'placeholder': 'Enter first name'}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'input-modern', 'placeholder': 'Enter last name'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'input-modern', 'placeholder': 'your@email.com', 'pattern': '^[^@\s]+@[^@\s]+\.[^@\s]{2,}$', 'oninvalid': "this.setCustomValidity('Please enter a valid email address (e.g., name@example.com).')", 'oninput': "this.setCustomValidity('')"}))
    contact_number = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'input-modern', 'placeholder': '09123456789', 'pattern': '^09\d{9}$', 'minlength': '11', 'maxlength': '11', 'inputmode': 'numeric'}))
