from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_premium = models.BooleanField(default=False)  # Added missing field
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
