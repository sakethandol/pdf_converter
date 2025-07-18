from django.contrib import admin
from .models import ConversionRequest

@admin.register(ConversionRequest)
class ConversionRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'original_filename', 'conversion_type', 'status', 'created_at')
    list_filter = ('conversion_type', 'status', 'created_at')
    search_fields = ('original_filename', 'user__username')
    readonly_fields = ('created_at', 'completed_at')