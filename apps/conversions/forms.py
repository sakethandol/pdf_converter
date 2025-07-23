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
            'original_file': forms.ClearableFileInput(attrs={  # CHANGED TO CLEARABLE
                'class': 'w-full px-3 py-2 border bg-gray-700 border-gray-800 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-white',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['conversion_type'].label = "Conversion Type"
        self.fields['original_file'].label = "Select File"
        
        # Make sure both fields are required
        self.fields['conversion_type'].required = True
        self.fields['original_file'].required = True
        
        # Set help text
        self.fields['original_file'].help_text = "Supported formats: PDF, DOC, DOCX, XLS, XLSX, PNG, JPG, JPEG (Max: 50MB)"
    
    def clean_original_file(self):
        """Custom validation for uploaded file"""
        uploaded_file = self.cleaned_data.get('original_file')
        
        if not uploaded_file:
            raise forms.ValidationError("Please select a file to upload.")
        
        # Check file size (limit to 50MB)
        if uploaded_file.size > 200 * 1024 * 1024:
            raise forms.ValidationError("File size cannot exceed 200MB.")
        
        # Check file extension (more flexible)
        allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg']
        file_name = uploaded_file.name.lower()
        
        # Get file extension
        if '.' in file_name:
            file_extension = '.' + file_name.split('.')[-1]
        else:
            raise forms.ValidationError("File must have an extension.")
        
        if file_extension not in allowed_extensions:
            raise forms.ValidationError(f"File type '{file_extension}' is not supported. Allowed types: {', '.join(allowed_extensions)}")
        
        return uploaded_file
    
    def clean_conversion_type(self):
        """Custom validation for conversion type"""
        conversion_type = self.cleaned_data.get('conversion_type')
        
        if not conversion_type:
            raise forms.ValidationError("Please select a conversion type.")
        
        # Validate conversion type is in allowed choices
        valid_choices = [choice[0] for choice in ConversionRequest.CONVERSION_TYPES]
        if conversion_type not in valid_choices:
            raise forms.ValidationError("Invalid conversion type selected.")
        
        return conversion_type
    
    def clean(self):
        """Overall form validation"""
        cleaned_data = super().clean()
        conversion_type = cleaned_data.get('conversion_type')
        uploaded_file = cleaned_data.get('original_file')
        
        # Validate file type matches conversion type
        if conversion_type and uploaded_file:
            file_extension = '.' + uploaded_file.name.lower().split('.')[-1]
            
            # Check if the input file type matches the conversion type
            conversion_rules = {
                'pdf_to_word': ['.pdf'],
                'word_to_pdf': ['.doc', '.docx'],
                'pdf_to_excel': ['.pdf'],
                'excel_to_pdf': ['.xls', '.xlsx'],
                'pdf_to_image': ['.pdf'],
                'image_to_pdf': ['.png', '.jpg', '.jpeg'],
            }
            
            expected_extensions = conversion_rules.get(conversion_type, [])
            if expected_extensions and file_extension not in expected_extensions:
                raise forms.ValidationError(
                    f"For {conversion_type.replace('_', ' ').title()}, please upload a file with extension: {', '.join(expected_extensions)}"
                )
        
        return cleaned_data