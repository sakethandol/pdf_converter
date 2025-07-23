from django.shortcuts import redirect, render
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic import TemplateView, CreateView
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm, CustomAuthenticationForm


def landing_page(request):
    return render(request, 'users/landing.html')


class HomeView(TemplateView):
    template_name = 'users/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            from apps.conversions.forms import FileUploadForm
            context['form'] = FileUploadForm()
        except ImportError:
            context['form'] = None
        context['is_authenticated'] = self.request.user.is_authenticated
        return context


class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    form_class = CustomAuthenticationForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('home')  # Redirect to home instead of dashboard
    
    def get_success_url(self):
        return reverse_lazy('home')


class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('login')  # Simple 'login' without namespace
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Registration successful! You can now log in.')
        return response


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('landing')  # Simple 'landing' without namespace