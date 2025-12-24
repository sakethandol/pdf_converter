import os
from django import forms
from .models import ConversionRequest

class FileUploadForm(forms.ModelForm):
    class Meta:
        model = ConversionRequest
        fields = ['conversion_type', 'original_file']
        widgets = {
            'conversion_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border bg-gray-700 border-gray-800 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-white'
            }),
            'original_file': forms.ClearableFileInput(attrs={
                'class': 'w-full px-3 py-2 border bg-gray-700 border-gray-800 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-white',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['conversion_type'].label = "Conversion Type"
        self.fields['original_file'].label = "Select File"
        self.fields['conversion_type'].required = True
        self.fields['original_file'].required = True
        # Match help text to validation limit (50MB is safer for web apps)
        self.fields['original_file'].help_text = "Supported: PDF, Word, Excel, Images (Max: 50MB)"
    
    def clean_original_file(self):
        uploaded_file = self.cleaned_data.get('original_file')
        
        if not uploaded_file:
            raise forms.ValidationError("Please select a file to upload.")
        
        # Consistent 50MB limit
        if uploaded_file.size > 50 * 1024 * 1024:
            raise forms.ValidationError("File size cannot exceed 50MB for stability.")
        
        # Robust extension check
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg']
        
        if ext not in allowed_extensions:
            raise forms.ValidationError(f"Type '{ext}' not supported.")
        
        return uploaded_file
    
    def clean(self):
        """Cross-field validation: Ensure file matches the action"""
        cleaned_data = super().clean()
        conversion_type = cleaned_data.get('conversion_type')
        uploaded_file = cleaned_data.get('original_file')
        
        if conversion_type and uploaded_file:
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            
            rules = {
                'pdf_to_word': ['.pdf'],
                'word_to_pdf': ['.doc', '.docx'],
                'pdf_to_excel': ['.pdf'],
                'excel_to_pdf': ['.xls', '.xlsx'],
                'pdf_to_image': ['.pdf'],
                'image_to_pdf': ['.png', '.jpg', '.jpeg'],
            }
            
            expected = rules.get(conversion_type, [])
            if ext not in expected:
                raise forms.ValidationError(
                    f"Invalid file for this conversion. Expected: {', '.join(expected)}"
                )
        
        return cleaned_data