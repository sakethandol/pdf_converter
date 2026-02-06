from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.base import ContentFile
import os

# Dynamic paths based on user status
def user_upload_path(instance, filename):
    uid = f"user_{instance.user.id}" if instance.user else "guest"
    return f'uploads/{uid}/{timezone.now().year}/{timezone.now().month}/{filename}'

def user_converted_path(instance, filename):
    uid = f"user_{instance.user.id}" if instance.user else "guest"
    return f'converted/{uid}/{timezone.now().year}/{timezone.now().month}/{filename}'

class ConversionRequest(models.Model):
    CONVERSION_TYPES = [
        ('pdf_to_word', 'PDF to Word'),
        ('word_to_pdf', 'Word to PDF'),
        ('pdf_to_excel', 'PDF to Excel'),
        ('excel_to_pdf', 'Excel to PDF'),
        ('pdf_to_image', 'PDF to Image'),
        ('image_to_pdf', 'Image to PDF'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    conversion_type = models.CharField(max_length=20, choices=CONVERSION_TYPES)
    original_file = models.FileField(upload_to=user_upload_path)
    converted_file = models.FileField(upload_to=user_converted_path, blank=True, null=True)
    original_filename = models.CharField(max_length=255)
    converted_filename = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField()
    status = models.CharField(max_length=20, default='pending')
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)
    download_count = models.IntegerField(default=0)

    def safe_process_conversion(self):
        """
        Main conversion logic with 'User-Lock' protection.
        Ensures the User object is not lost during the file save process.
        """
        # 1. Capture the user at the very start to prevent losing relation in memory
        original_user = self.user 
        
        try:
            self.status = 'processing'
            # Save ONLY status to avoid touching the User relation column yet
            self.save(update_fields=['status'])

            from .converters import FileConverter
            success, content_bytes, message = FileConverter.convert_file(
                self.conversion_type, 
                self.original_file.path
            )

            if success and content_bytes:
                self.converted_filename = self.generate_converted_filename()
                
                # CRITICAL: Use save=False to attach the file without a DB commit
                self.converted_file.save(self.converted_filename, ContentFile(content_bytes), save=False)
                
                self.status = 'completed'
                self.completed_at = timezone.now()
                
                # 2. Re-affirm the user right before the final database commit
                self.user = original_user 
                
                # 3. Final Save (Updates user, status, and file link in one atomic transaction)
                self.save() 
                return True
            else:
                raise Exception(message or "Conversion logic failed")
        except Exception as e:
            self.status = 'failed'
            self.error_message = str(e)
            self.user = original_user # Re-affirm even on failure
            self.save()
            return False

    def generate_converted_filename(self):
        name = os.path.splitext(self.original_filename)[0]
        ext = {
            'pdf_to_word': '.docx', 'word_to_pdf': '.pdf',
            'pdf_to_excel': '.xlsx', 'excel_to_pdf': '.pdf',
            'pdf_to_image': '.png', 'image_to_pdf': '.pdf',
        }.get(self.conversion_type, '.pdf')
        return f"{name}_converted{ext}"

    def get_download_url(self):
        """Utility to get the correct URL for templates"""
        if self.user:
            return f"/converter/download/{self.id}/"
        return f"/converter/guest-download/{self.id}/"

    def __str__(self):
        return f"{self.original_filename} - {self.status}"