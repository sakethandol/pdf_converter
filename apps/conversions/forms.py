from django import forms
from .models import ConversionRequest

class FileUploadForm(forms.ModelForm):
    class Meta:
        model = ConversionRequest
        fields = ['conversion_type', 'original_file']
        widgets = {
            'conversion_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'original_file': forms.FileInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['conversion_type'].label = "Conversion Type"
        self.fields['original_file'].label = "Select File"