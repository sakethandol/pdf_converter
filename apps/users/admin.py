from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'is_premium', 'created_at')
    list_filter = ('is_premium', 'created_at')
    search_fields = ('user__username', 'user__email')