from django.shortcuts import render

def login_view(request):
    return render(request, "login.html")

def register_view(request):
    return render(request, 'register.html')

#@login_required
def dashboard(request):
    return render(request, 'dashboard.html')