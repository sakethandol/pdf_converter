from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import os
import shutil
import uuid
from pathlib import Path

def user_upload_path(instance, filename):
    """Generate upload path: uploads/user_id/year/month/filename"""
    # ✅ FIX: More robust user handling
    unique_id = uuid.uuid4().hex[:6]
    name, ext = os.path.splitext(filename)
    unique_filename = f"{name}_{unique_id}{ext}"
    
    # ✅ CRITICAL FIX: Better user detection
    user_id = None
    if hasattr(instance, 'user') and instance.user:
        user_id = instance.user.id
    elif hasattr(instance, '_original_user') and instance._original_user:
        user_id = instance._original_user.id
    
    if user_id:
        return f'uploads/user_{user_id}/{timezone.now().year}/{timezone.now().month}/{unique_filename}'
    else:
        return f'uploads/guest/{timezone.now().year}/{timezone.now().month}/{unique_filename}'

def user_converted_path(instance, filename):
    """Generate converted file path: converted/user_id/year/month/filename"""
    # ✅ FIX: More robust user handling
    unique_id = uuid.uuid4().hex[:6]
    name, ext = os.path.splitext(filename)
    unique_filename = f"{name}_{unique_id}{ext}"

    name, ext = os.path.splitext(filename)
    if not ext:  # Add extension if missing
        ext = instance.get_converted_extension()
    unique_filename = f"{name}_{unique_id}{ext}"
    
    # ✅ CRITICAL FIX: Better user detection
    user_id = None
    if hasattr(instance, 'user') and instance.user:
        user_id = instance.user.id
    elif hasattr(instance, '_original_user') and instance._original_user:
        user_id = instance._original_user.id
    
    if user_id:
        return f'converted/user_{user_id}/{timezone.now().year}/{timezone.now().month}/{unique_filename}'
    else:
        return f'converted/guest/{timezone.now().year}/{timezone.now().month}/{unique_filename}'

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
        unique_id = uuid.uuid4().hex[:6]
        return f"{name_without_ext}_converted_{unique_id}{new_extension}"
    
    def safe_process_conversion(self):
        """Ultra-safe conversion method that preserves user at all costs"""
        # ✅ STEP 1: Lock in the user immediately
        original_user = self.user
        original_user_id = self.user.id if self.user else None
        
        # ✅ STEP 2: Store user as backup attribute
        self._original_user = original_user
        
        print(f"🔒 LOCKED USER: {original_user} (ID: {original_user_id})")
        
        try:
            # Update to processing
            self.status = 'processing'
            if original_user:
                self.user = original_user
            
            # ✅ STEP 3: Save with explicit user preservation
            ConversionRequest.objects.filter(id=self.id).update(
                status='processing',
                user=original_user
            )
            
            # Generate filename
            self.converted_filename = self.generate_converted_filename()
            original_path = self.original_file.path
            
            if not os.path.exists(original_path):
                raise Exception(f"Original file not found at: {original_path}")
            
            # Perform conversion
            converted_content = self.perform_conversion(original_path)
            
            if not converted_content:
                raise Exception("Conversion failed - no content returned")
            
            # ✅ STEP 4: Save file with user locked
            if original_user:
                self.user = original_user
                
            # Save converted file to storage AND update model
            self.converted_file.save(
                self.converted_filename,
                ContentFile(converted_content),
                save=True  # CHANGED: Must save model to update FileField
            )
        
            
            # ✅ STEP 5: Final update with explicit SQL
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save(update_fields=['status', 'completed_at'])
            
            # Refresh instance
            self.refresh_from_db()
            
            print(f"✅ CONVERSION COMPLETED - User preserved: {self.user}")
            return True
            
        except Exception as e:
            print(f"❌ CONVERSION FAILED: {e}")
            
            # ✅ STEP 6: Even failures preserve user
            ConversionRequest.objects.filter(id=self.id).update(
                status='failed',
                error_message=str(e),
                user=original_user  # Preserve user even on failure
            )
            
            self.refresh_from_db()
            return False
        
        finally:
            # ✅ STEP 7: Final safety check
            if self.user != original_user:
                print(f"🚨 USER LOST! Restoring {original_user}")
                ConversionRequest.objects.filter(id=self.id).update(user=original_user)
                self.user = original_user
    
    def process_conversion(self):
        """Legacy conversion method - kept for backward compatibility"""
        # ✅ CRITICAL FIX: Store the original user at the very beginning
        original_user = self.user
        
        try:
            print(f"Starting conversion for: {self.original_filename}")
            print(f"User before processing: {self.user} (ID: {self.user.id if self.user else None})")
            
            # ✅ FIX: Update status WITHOUT calling save() yet
            self.status = 'processing'
            
            # Generate converted filename
            self.converted_filename = self.generate_converted_filename()
            print(f"Generated filename: {self.converted_filename}")
            
            # Get the original file path
            original_path = self.original_file.path
            print(f"Original file path: {original_path}")
            
            # Check if original file exists
            if not os.path.exists(original_path):
                raise Exception(f"Original file not found at: {original_path}")
            
            # ✅ CRITICAL FIX: Save the processing status with user preserved
            if original_user:
                self.user = original_user
            self.save(update_fields=['status', 'user'])  # Only update specific fields
            
            # Perform actual conversion
            converted_content = self.perform_conversion(original_path)
            
            if converted_content:
                print(f"Conversion successful, saving file...")
                
                # ✅ CRITICAL FIX: Ensure user is set BEFORE file operations
                if original_user:
                    self.user = original_user
                
                # Save the converted file
                self.converted_file.save(
                    self.converted_filename,
                    ContentFile(converted_content),
                    save=False  # Don't save the model yet
                )
                
                # Set completion fields
                self.status = 'completed'
                self.completed_at = timezone.now()
                
                print(f"Conversion completed successfully")
            else:
                raise Exception("Conversion failed - no content returned")
                
        except Exception as e:
            print(f"Conversion error: {e}")
            self.status = 'failed'
            self.error_message = str(e)
            raise e
        
        finally:
            # ✅ CRITICAL FIX: ALWAYS restore user in finally block
            if original_user:
                self.user = original_user
            
            # Final save with all fields
            self.save()
            
            # ✅ VERIFICATION: Check if user was preserved
            self.refresh_from_db()
            if original_user and self.user != original_user:
                print(f"CRITICAL ERROR: User was lost after save! Expected: {original_user}, Got: {self.user}")
                # Emergency fix - force user assignment
                ConversionRequest.objects.filter(id=self.id).update(user=original_user)
                self.user = original_user
                print(f"User emergency restoration: {self.user}")
        
        print(f"Final user after processing: {self.user} (ID: {self.user.id if self.user else None})")
        return self.status == 'completed'
    
    def perform_conversion(self, original_path):
        """
        Perform actual file conversion using proper conversion libraries.
        """
        try:
            print(f"Starting conversion: {self.conversion_type}")
            print(f"Input file: {original_path}")
            
            from .converters import FileConverter
            
            # Use the new convert_file method
            success, content_bytes, message = FileConverter.convert_file(
                self.conversion_type, 
                original_path
            )
            
            print(f"Conversion result: success={success}, message='{message}'")
            
            if success and content_bytes:
                print(f"Conversion successful, content size: {len(content_bytes)} bytes")
                return content_bytes
            else:
                error_msg = message or "Conversion failed"
                print(f"Conversion failed: {error_msg}")
                raise Exception(error_msg)
                
        except ImportError as e:
            error_msg = f"Missing conversion library: {str(e)}"
            print(error_msg)
            return None
        except Exception as e:
            error_msg = f"Conversion error: {str(e)}"
            print(error_msg)
            return None
    
    def get_download_url(self):
        """Get the appropriate download URL based on user type"""
        if self.user:
            return f"/converter/download/{self.id}/"
        else:
            return f"/converter/guest-download/{self.id}/"