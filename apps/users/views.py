from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import CustomUserCreationForm, CustomAuthenticationForm

def home(request):
    return render(request, 'users/home.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        email = request.POST.get('email', '').strip()
        
        # Validation
        if not username:
            messages.error(request, "Username is required")
        elif not password1:
            messages.error(request, "Password is required")
        elif password1 != password2:
            messages.error(request, "Passwords do not match")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
        else:
            try:
                user = User.objects.create_user(
                    username=username,
                    password=password1,
                    email=email
                )
                
                # Create UserProfile
                from .models import UserProfile
                UserProfile.objects.create(user=user)
                
                # Login the user
                user = authenticate(username=username, password=password1)
                if user:
                    login(request, user)
                    return redirect('/login/')
                    
            except Exception as e:
                messages.error(request, f"Error creating user: {str(e)}")
    
    return render(request, 'users/register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('/dashboard/')
            else:
                messages.error(request, "Invalid username or password")
        else:
            messages.error(request, "Please enter both username and password")
    
    return render(request, 'users/login.html')

@login_required
def dashboard(request):
    return render(request, 'users/dashboard.html')

def logout_view(request):
    logout(request)
    return redirect('/')