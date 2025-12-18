from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages

# Custom logout function to handle success messages
def simple_logout(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('users:login') # Redirecting to login is standard after logout

urlpatterns = [
    # Admin Interface
    path('admin/', admin.site.urls),
    
    # Auth Management
    path('logout/', simple_logout, name='logout'),
    
    # App-specific routes
    # Note: We use the namespace defined inside the app's urls.py
    path('converter/', include('apps.conversions.urls')),
    
    # Landing page and user authentication
    path('', include('apps.users.urls')),
]

# Serve static and media files during development
# This is CRITICAL for your PDF downloads and CSS/JS to work
if settings.DEBUG:
    # Standard static files (CSS, JS)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Uploaded and Converted files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)