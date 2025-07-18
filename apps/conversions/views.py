from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponse, Http404, FileResponse, JsonResponse
from django.views.generic import FormView, DetailView, ListView, TemplateView, View
from django.urls import reverse_lazy
from django.utils.encoding import smart_str
from django.conf import settings
from django.core.paginator import Paginator
import os
import mimetypes
from .models import ConversionRequest
from .forms import FileUploadForm

class FileUploadView(LoginRequiredMixin, FormView):
    """File upload view for authenticated users"""
    template_name = 'conversions/upload.html'
    form_class = FileUploadForm
    login_url = '/login/'
    
    def form_valid(self, form):
        conversion = form.save(commit=False)
        conversion.user = self.request.user
        conversion.original_filename = self.request.FILES['original_file'].name
        conversion.file_size = self.request.FILES['original_file'].size
        conversion.save()
        
        # Process conversion
        conversion.process_conversion()
        
        messages.success(self.request, 'File uploaded and converted successfully!')
        return redirect('conversions:convert_detail', conversion_id=conversion.id)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class GuestConvertView(FormView):
    """File conversion view for guest users"""
    template_name = 'conversions/upload.html'
    form_class = FileUploadForm
    
    def form_valid(self, form):
        conversion = form.save(commit=False)
        conversion.user = None
        conversion.original_filename = self.request.FILES['original_file'].name
        conversion.file_size = self.request.FILES['original_file'].size
        conversion.save()
        
        conversion.process_conversion()
        
        return redirect('conversions:guest_result', conversion_id=conversion.id)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class ConversionDetailView(LoginRequiredMixin, DetailView):
    """View conversion details for authenticated users"""
    model = ConversionRequest
    template_name = 'conversions/result.html'
    context_object_name = 'conversion'
    pk_url_kwarg = 'conversion_id'
    login_url = '/login/'
    
    def get_queryset(self):
        return ConversionRequest.objects.filter(user=self.request.user)

class GuestResultView(DetailView):
    """View conversion results for guest users"""
    model = ConversionRequest
    template_name = 'conversions/result.html'
    context_object_name = 'conversion'
    pk_url_kwarg = 'conversion_id'
    
    def get_queryset(self):
        return ConversionRequest.objects.filter(user=None)

class ConversionHistoryView(LoginRequiredMixin, ListView):
    """View conversion history for authenticated users"""
    model = ConversionRequest
    template_name = 'conversions/history.html'
    context_object_name = 'conversions'
    login_url = '/login/'
    paginate_by = 10  # Show 10 conversions per page
    
    def get_queryset(self):
        return ConversionRequest.objects.filter(user=self.request.user).order_by('-created_at')

class FileDownloadView(LoginRequiredMixin, View):
    """Handle file downloads for authenticated users"""
    login_url = '/login/'
    
    def get(self, request, file_id):
        # Get the conversion object
        conversion = get_object_or_404(
            ConversionRequest, 
            id=file_id, 
            user=request.user,
            status='completed'
        )
        
        # Check if converted file exists
        if not conversion.converted_file:
            messages.error(request, 'Converted file not found.')
            return redirect('conversions:history')
        
        # Get the file path
        file_path = conversion.converted_file.path
        
        if not os.path.exists(file_path):
            messages.error(request, 'File not found on server.')
            return redirect('conversions:history')
        
        # Update download count
        conversion.download_count += 1
        conversion.save()
        
        # Serve the file
        try:
            response = FileResponse(
                open(file_path, 'rb'),
                as_attachment=True,
                filename=conversion.converted_filename or f"converted_{conversion.original_filename}"
            )
            return response
        except Exception as e:
            messages.error(request, f'Error downloading file: {str(e)}')
            return redirect('conversions:history')

class GuestDownloadView(View):
    """Handle file downloads for guest users"""
    
    def get(self, request, file_id):
        # Get the conversion object for guest user
        conversion = get_object_or_404(
            ConversionRequest, 
            id=file_id, 
            user=None,  # Guest user
            status='completed'
        )
        
        # Check if converted file exists
        if not conversion.converted_file:
            messages.error(request, 'Converted file not found.')
            return redirect('conversions:guest_result', conversion_id=conversion.id)
        
        # Get the file path
        file_path = conversion.converted_file.path
        
        if not os.path.exists(file_path):
            messages.error(request, 'File not found on server.')
            return redirect('conversions:guest_result', conversion_id=conversion.id)
        
        # Update download count
        conversion.download_count += 1
        conversion.save()
        
        # Get proper filename
        filename = conversion.converted_filename or f"converted_{conversion.original_filename}"
        
        # Serve the file
        try:
            response = FileResponse(
                open(file_path, 'rb'),
                as_attachment=True,
                filename=filename
            )
            return response
        except Exception as e:
            messages.error(request, f'Error downloading file: {str(e)}')
            return redirect('conversions:guest_result', conversion_id=conversion.id)

class ConvertFileView(TemplateView):
    """Legacy convert file view"""
    template_name = 'conversions/result.html'

class ConversionStatusView(View):
    """AJAX endpoint to check conversion status"""
    
    def get(self, request, conversion_id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                if request.user.is_authenticated:
                    conversion = get_object_or_404(
                        ConversionRequest, 
                        id=conversion_id, 
                        user=request.user
                    )
                else:
                    conversion = get_object_or_404(
                        ConversionRequest, 
                        id=conversion_id, 
                        user=None
                    )
                
                data = {
                    'status': conversion.status,
                    'error_message': conversion.error_message,
                    'completed_at': conversion.completed_at.isoformat() if conversion.completed_at else None,
                }
                return JsonResponse(data)
            except ConversionRequest.DoesNotExist:
                return JsonResponse({'error': 'Conversion not found'}, status=404)
        
        return JsonResponse({'error': 'Invalid request'}, status=400)

class DeleteConversionView(LoginRequiredMixin, View):
    """Delete a conversion (authenticated users only)"""
    login_url = '/login/'
    
    def post(self, request, conversion_id):
        conversion = get_object_or_404(
            ConversionRequest, 
            id=conversion_id, 
            user=request.user
        )
        
        # Delete files from storage
        if conversion.original_file:
            try:
                conversion.original_file.delete()
            except:
                pass
        
        if conversion.converted_file:
            try:
                conversion.converted_file.delete()
            except:
                pass
        
        # Delete the record
        conversion.delete()
        messages.success(request, 'Conversion deleted successfully.')
        
        return redirect('conversions:history')
    
    def get(self, request, conversion_id):
        # Redirect to history if accessed via GET
        return redirect('conversions:history')