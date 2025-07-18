from django.shortcuts import redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic import TemplateView, CreateView
from django.contrib.auth.views import LoginView, LogoutView
from .forms import CustomUserCreationForm, CustomAuthenticationForm
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
        if self.request.user.is_authenticated:
            context['username'] = self.request.user.username
        return context
class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    form_class = CustomAuthenticationForm
    redirect_authenticated_user = False
class RegisterView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'users/register.html'
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'users/dashboard.html'
    login_url = '/login/'
    redirect_field_name = 'next'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            from apps.conversions.models import ConversionRequest
            recent_conversions = ConversionRequest.objects.filter(
                user=self.request.user
            ).order_by('-created_at')[:5]
            context['recent_conversions'] = recent_conversions
            context['total_conversions'] = ConversionRequest.objects.filter(
                user=self.request.user
            ).count()
        except ImportError:
            context['recent_conversions'] = []
            context['total_conversions'] = 0
        return context
class CustomLogoutView(LogoutView):
    next_page = '/'
