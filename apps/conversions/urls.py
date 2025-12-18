from django.urls import path
from . import views

app_name = 'conversions'

urlpatterns = [
    # --- Upload & Conversion ---
    path('upload/', views.FileUploadView.as_view(), name='upload'),
    path('guest-convert/', views.GuestConvertView.as_view(), name='guest_convert'),
    
    # --- Downloads ---
    # Both names point to FileDownloadView because it now handles both User and Guest logic
    path('download/<int:file_id>/', views.FileDownloadView.as_view(), name='download'),
    path('guest-download/<int:file_id>/', views.FileDownloadView.as_view(), name='guest_download'),
    
    # --- Results & Details ---
    path('result/<int:conversion_id>/', views.ConversionDetailView.as_view(), name='convert_detail'),
    path('guest-result/<int:conversion_id>/', views.GuestResultView.as_view(), name='guest_result'),
    
    # --- Retry conversion ---
    path('retry/<int:conversion_id>/', views.RetryConversionView.as_view(), name='retry'),
    
    # --- History & Dashboard ---
    path('history/', views.ConversionHistoryView.as_view(), name='history'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # --- Status & Management ---
    path('status/<int:conversion_id>/', views.ConversionStatusView.as_view(), name='status'),
    path('delete/<int:conversion_id>/', views.DeleteConversionView.as_view(), name='delete'),
]