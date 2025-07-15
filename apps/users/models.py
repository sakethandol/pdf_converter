from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

class ConversionHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    original_filename = models.CharField(max_length=255)
    converted_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    conversion_type = models.CharField(max_length=50) 
    created_at = models.DateTimeField(default=timezone.now)
    download_count = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username} - {self.original_filename}"
    
    class Meta:
        ordering = ['-created_at']