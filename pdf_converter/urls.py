from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages

def simple_logout(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('/')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('logout/', simple_logout, name='simple_logout'),  # Add this temporarily
    path('converter/', include('apps.conversions.urls',namespace='conversions')),
    path('', include('apps.users.urls')),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)