from django.contrib import admin

from .models import UserProfile, ConversionHistory

admin.site.register(UserProfile)
admin.site.register(ConversionHistory)
