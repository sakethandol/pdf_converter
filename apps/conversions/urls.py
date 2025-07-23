from django.urls import path
from . import views

app_name = 'conversions'

urlpatterns = [
    # Upload and conversion
    path('upload/', views.FileUploadView.as_view(), name='upload'),
    path('guest-convert/', views.GuestConvertView.as_view(), name='guest_convert'),
    
    # Results and details
    path('result/<int:conversion_id>/', views.ConversionDetailView.as_view(), name='convert_detail'),
    path('guest-result/<int:conversion_id>/', views.GuestResultView.as_view(), name='guest_result'),
    
    # History
    path('history/', views.ConversionHistoryView.as_view(), name='history'),

    
    
    # Downloads
    path('download/<int:file_id>/', views.FileDownloadView.as_view(), name='download'),
    path('guest-download/<int:file_id>/', views.GuestDownloadView.as_view(), name='guest_download'),
    
    # Status and management
    path('status/<int:conversion_id>/', views.ConversionStatusView.as_view(), name='status'),
    path('delete/<int:conversion_id>/', views.DeleteConversionView.as_view(), name='delete'),
    
    # Dashboard (if you want it in conversions app)
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
]