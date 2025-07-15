from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os

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
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    conversion_type = models.CharField(max_length=20, choices=CONVERSION_TYPES)
    original_file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    converted_file = models.FileField(upload_to='converted/%Y/%m/%d/', blank=True, null=True)
    original_filename = models.CharField(max_length=255)
    converted_filename = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)
    download_count = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username} - {self.conversion_type} - {self.original_filename}"
    
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