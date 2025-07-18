from django.urls import path
from . import views

app_name = 'conversions'  # Fixed namespace

urlpatterns = [
    path('upload/', views.FileUploadView.as_view(), name='upload'),
    path('convert/', views.ConvertFileView.as_view(), name='convert'),
    path('convert/<int:conversion_id>/', views.ConversionDetailView.as_view(), name='convert_detail'),
    path('download/<int:file_id>/', views.FileDownloadView.as_view(), name='download'),
    path('history/', views.ConversionHistoryView.as_view(), name='history'),
    
    # Guest user URLs
    path('guest-convert/', views.GuestConvertView.as_view(), name='guest_convert'),
    path('guest-result/<int:conversion_id>/', views.GuestResultView.as_view(), name='guest_result'),
    path('guest-download/<int:file_id>/', views.GuestDownloadView.as_view(), name='guest_download'),
    
    # Additional URLs
    path('status/<int:conversion_id>/', views.ConversionStatusView.as_view(), name='conversion_status'),
    path('delete/<int:conversion_id>/', views.DeleteConversionView.as_view(), name='delete_conversion'),
]