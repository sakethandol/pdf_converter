from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.base import ContentFile
import os

def user_upload_path(instance, filename):
    """Generate upload path: uploads/user_id/year/month/filename"""
    user_segment = f"user_{instance.user.id}" if instance.user else "guest"
    return f'uploads/{user_segment}/{timezone.now().year}/{timezone.now().month}/{filename}'

def user_converted_path(instance, filename):
    """Generate converted file path: converted/user_id/year/month/filename"""
    user_segment = f"user_{instance.user.id}" if instance.user else "guest"
    return f'converted/{user_segment}/{timezone.now().year}/{timezone.now().month}/{filename}'

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
    
    class Meta:
        ordering = ['-created_at']

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
        name_without_ext = os.path.splitext(self.original_filename)[0]
        return f"{name_without_ext}_converted{self.get_converted_extension()}"

    def safe_process_conversion(self):
        """
        The single source of truth for conversion. 
        Uses Atomic updates to prevent User loss.
        """
        # 1. Store the user in memory immediately
        current_user = self.user
        
        try:
            # 2. Set to processing
            self.status = 'processing'
            self.save(update_fields=['status'])
            
            # 3. Perform conversion
            original_path = self.original_file.path
            if not os.path.exists(original_path):
                raise Exception("Original file missing from server.")

            from .converters import FileConverter
            success, content_bytes, message = FileConverter.convert_file(
                self.conversion_type, 
                original_path
            )
            
            if success and content_bytes:
                # 4. Prepare the file and metadata
                self.converted_filename = self.generate_converted_filename()
                
                # We use save=False here to prevent the intermediate save 
                # that often triggers the user-loss bug.
                self.converted_file.save(
                    self.converted_filename,
                    ContentFile(content_bytes),
                    save=False
                )
                
                self.status = 'completed'
                self.completed_at = timezone.now()
                self.user = current_user  # Re-affirm user before final save
                self.save()
                return True
            else:
                raise Exception(message or "Conversion logic failed.")
                
        except Exception as e:
            self.status = 'failed'
            self.error_message = str(e)
            self.user = current_user
            self.save()
            return False

    def get_download_url(self):
        if self.user:
            return f"/converter/download/{self.id}/"
        return f"/converter/guest-download/{self.id}/"