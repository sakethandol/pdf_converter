from django.urls import path
from . import views

app_name = 'apps.users'

urlpatterns = [
    path('', views.landing_page, name='landing'),                  
    path('home/', views.HomeView.as_view(), name='home'), 
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
]