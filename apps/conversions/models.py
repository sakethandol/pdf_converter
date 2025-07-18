from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import os
import shutil
from pathlib import Path

def user_upload_path(instance, filename):
    """Generate upload path: uploads/user_id/year/month/filename"""
    if instance.user:
        return f'uploads/{instance.user.id}/{timezone.now().year}/{timezone.now().month}/{filename}'
    else:
        return f'uploads/guest/{timezone.now().year}/{timezone.now().month}/{filename}'

def user_converted_path(instance, filename):
    """Generate converted file path: converted/user_id/year/month/filename"""
    if instance.user:
        return f'converted/{instance.user.id}/{timezone.now().year}/{timezone.now().month}/{filename}'
    else:
        return f'converted/guest/{timezone.now().year}/{timezone.now().month}/{filename}'

class ConversionRequest(models.Model):
    CONVERSION_TYPES = [
        ('pdf_to_word', 'PDF to Word'),
        ('word_to_pdf', 'Word to PDF'),
        ('pdf_to_excel', 'PDF to Excel'),
        ('excel_to_pdf', 'Excel to PDF'),
        ('pdf_to_image', 'PDF to Image'),
        ('image_to_pdf', 'Image to PDF'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    conversion_type = models.CharField(max_length=20, choices=CONVERSION_TYPES)
    original_file = models.FileField(upload_to=user_upload_path)
    converted_file = models.FileField(upload_to=user_converted_path, blank=True, null=True)
    original_filename = models.CharField(max_length=255)
    converted_filename = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)
    download_count = models.IntegerField(default=0)
    
    def __str__(self):
        user_str = self.user.username if self.user else "Guest"
        return f"{user_str} - {self.conversion_type} - {self.original_filename}"
    
    class Meta:
        ordering = ['-created_at']

    def get_file_extension(self):
        return os.path.splitext(self.original_filename)[1].lower()
    
    def get_converted_extension(self):
        conversion_map = {
            'pdf_to_word': '.docx',
            'word_to_pdf': '.pdf',
            'pdf_to_excel': '.xlsx',
            'excel_to_pdf': '.pdf',
            'pdf_to_image': '.png',
            'image_to_pdf': '.pdf',
        }
        return conversion_map.get(self.conversion_type, '.pdf')
    
    def generate_converted_filename(self):
        """Generate the converted filename"""
        name_without_ext = os.path.splitext(self.original_filename)[0]
        new_extension = self.get_converted_extension()
        return f"{name_without_ext}_converted{new_extension}"
    
    def process_conversion(self):
        """Process the actual file conversion"""
        try:
            self.status = 'processing'
            self.save()
            
            # Generate converted filename
            self.converted_filename = self.generate_converted_filename()
            
            # For now, we'll simulate conversion by copying the original file
            # with a new extension. You can replace this with actual conversion logic later
            original_path = self.original_file.path
            
            # Create a temporary converted file (simulation)
            # In real implementation, you'd use libraries like python-docx, pypdf2, etc.
            converted_content = self.simulate_conversion(original_path)
            
            if converted_content:
                # Save the converted file
                converted_file_path = user_converted_path(self, self.converted_filename)
                self.converted_file.save(
                    self.converted_filename,
                    ContentFile(converted_content),
                    save=False
                )
                
                self.status = 'completed'
                self.completed_at = timezone.now()
            else:
                raise Exception("Conversion failed")
                
        except Exception as e:
            self.status = 'failed'
            self.error_message = str(e)
        
        self.save()
        return self.status == 'completed'
    
    def perform_conversion(self, original_path):
        """
        Perform actual file conversion using proper conversion libraries.
        """
        try:
            from .converters import FileConverter
            
            # Use the new convert_file method
            success, content_bytes, message = FileConverter.convert_file(
                self.conversion_type, 
                original_path
            )
            
            if success and content_bytes:
                return content_bytes
            else:
                raise Exception(message or "Conversion failed")
                
        except Exception as e:
            print(f"Conversion error: {e}")
            return None
    
    # Alias for backward compatibility
    def simulate_conversion(self, original_path):
        """Alias for perform_conversion for backward compatibility"""
        return self.perform_conversion(original_path)
    
    def get_download_url(self):
        """Get the appropriate download URL based on user type"""
        if self.user:
            return f"/converter/download/{self.id}/"
        else:
            return f"/converter/guest-download/{self.id}/"