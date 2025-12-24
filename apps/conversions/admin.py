from django.contrib import admin
from .models import ConversionRequest

@admin.register(ConversionRequest)
class ConversionRequestAdmin(admin.ModelAdmin):
    # ✅ Enhanced list_display to show the actual username clearly
    list_display = ('display_user', 'original_filename', 'conversion_type', 'status', 'created_at', 'download_count')
    
    # Filters on the right sidebar
    list_filter = ('conversion_type', 'status', 'created_at')
    
    # Search functionality
    search_fields = ('original_filename', 'user__username', 'error_message')
    
    # Read-only fields to prevent manual tampering with logs
    readonly_fields = ('created_at', 'completed_at', 'file_size', 'download_count')
    
    # Organization of the detail view
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('File Details', {
            'fields': ('original_filename', 'original_file', 'converted_filename', 'converted_file', 'file_size')
        }),
        ('Conversion Status', {
            'fields': ('conversion_type', 'status', 'error_message', 'download_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at')
        }),
    )

    def display_user(self, obj):
        """Custom method to ensure the username is shown instead of a hyphen."""
        if obj.user:
            return obj.user.username
        return "Guest"
    
    # Sets the column header name in the admin list
    display_user.short_description = 'User'
    
    # Allows sorting by user in the admin list
    display_user.admin_order_field = 'user'