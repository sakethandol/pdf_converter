from django.urls import path
from . import views

app_name = 'apps.conversions'

urlpatterns = [
    path('upload/', views.upload_file, name='upload'),
    path('convert/', views.convert_file, name='convert'),
    path('download/<int:file_id>/', views.download_file, name='download'),
    path('history/', views.conversion_history, name='history'),
]