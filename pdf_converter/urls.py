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
    return redirect('users:login') # Ensure 'users:login' matches your users/urls.py name

urlpatterns = [
    # Admin Interface
    path('admin/', admin.site.urls),
    
    # Auth Management
    path('logout/', simple_logout, name='logout'),
    
    # App-specific routes
    # Linking to your conversions app
    path('converter/', include('apps.conversions.urls')),
    
    # Landing page and user authentication (Login/Register)
    path('', include('apps.users.urls')),
]

# --- THE CRITICAL MEDIA/STATIC ADDITION ---
# This allows Django to serve the PDFs generated in your 'media' folder 
# and the CSS/JS files in your 'static' folder while you are developing.
if settings.DEBUG:
    # 1. Serve static files (CSS, JavaScript, Images for UI)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # 2. Serve media files (Uploaded files and the CONVERTED PDFs)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)