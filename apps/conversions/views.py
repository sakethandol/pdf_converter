from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponse, Http404, FileResponse, JsonResponse
from django.views.generic import FormView, DetailView, ListView, TemplateView, View
from django.utils import timezone
from datetime import timedelta
import os

from django.conf import settings 
from .models import ConversionRequest
from .forms import FileUploadForm

class FileUploadView(LoginRequiredMixin, FormView):
    """View for authenticated users to upload and convert files"""
    template_name = 'conversions/upload.html'
    form_class = FileUploadForm
    login_url = '/login/'
    
    def form_valid(self, form):
        try:
            # STEP 1: Create the object but don't save to DB yet
            conversion = form.save(commit=False)
            
            # STEP 2: Manually attach the logged-in user
            conversion.user = self.request.user
            
            # STEP 3: Handle file metadata
            uploaded_file = self.request.FILES.get('original_file')
            conversion.original_filename = uploaded_file.name
            conversion.file_size = uploaded_file.size
            
            # STEP 4: Save to the database immediately
            # This 'locks' the User ID into the record before conversion starts
            conversion.save() 
            
            # STEP 5: Run conversion
            success = conversion.safe_process_conversion()
            
            if success:
                messages.success(self.request, 'Converted successfully!')
            else:
                messages.warning(self.request, f'Failed: {conversion.error_message}')
                
            return redirect('conversions:convert_detail', conversion_id=conversion.id)
            
        except Exception as e:
            messages.error(self.request, f'Error: {str(e)}')
            return self.form_invalid(form)

class GuestConvertView(FormView):
    """Conversion view for non-logged in guest users using session storage"""
    template_name = 'conversions/upload.html'
    form_class = FileUploadForm
    
    def form_valid(self, form):
        try:
            conversion = form.save(commit=False)
            conversion.user = None # Explicitly guest
            uploaded_file = self.request.FILES.get('original_file')
            
            conversion.original_filename = uploaded_file.name
            conversion.file_size = uploaded_file.size
            conversion.save()
            
            success = conversion.safe_process_conversion()
            
            guest_list = self.request.session.get('guest_conversions', [])
            guest_list.append(conversion.id)
            self.request.session['guest_conversions'] = guest_list
            self.request.session.modified = True
            
            if success:
                messages.success(self.request, 'Converted successfully!')
            return redirect('conversions:guest_result', conversion_id=conversion.id)
        except Exception as e:
            messages.error(self.request, f'Error: {str(e)}')
            return self.form_invalid(form)

class FileDownloadView(View):
    """Atomic download logic handling both Auth and Guest users"""
    def get(self, request, file_id):
        conversion = get_object_or_404(ConversionRequest, id=file_id)
        
        is_owner = request.user.is_authenticated and conversion.user == request.user
        is_guest_allowed = (conversion.user is None and file_id in request.session.get('guest_conversions', []))
        
        if not (is_owner or is_guest_allowed):
            messages.error(request, "Permission denied.")
            return redirect('conversions:history') if request.user.is_authenticated else redirect('/')

        if conversion.status != 'completed' or not conversion.converted_file:
            messages.error(request, "Converted file is not available.")
            return redirect('conversions:history') if request.user.is_authenticated else redirect('/')

        try:
            file_handle = conversion.converted_file.open('rb')
            response = FileResponse(file_handle, as_attachment=True)
            response['Content-Disposition'] = f'attachment; filename="{conversion.converted_filename}"'
            
            # Atomic update for download count
            ConversionRequest.objects.filter(id=file_id).update(download_count=conversion.download_count + 1)
            return response
        except Exception as e:
            messages.error(request, f"Download failed: {str(e)}")
            return redirect('conversions:history')

class ConversionHistoryView(LoginRequiredMixin, ListView):
    model = ConversionRequest
    template_name = 'conversions/history.html'
    context_object_name = 'conversions'
    paginate_by = 10

    def get_queryset(self):
        return ConversionRequest.objects.filter(user=self.request.user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_convs = ConversionRequest.objects.filter(user=self.request.user)
        context.update({
            'total_conversions': user_convs.count(),
            'completed_conversions': user_convs.filter(status='completed').count(),
            'failed_conversions': user_convs.filter(status='failed').count(),
            'success_rate': round((user_convs.filter(status='completed').count() / user_convs.count() * 100) if user_convs.exists() else 0, 1),
        })
        return context

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_conversions'] = ConversionRequest.objects.filter(user=self.request.user).order_by('-created_at')[:5]
        return context

class ConversionDetailView(DetailView):
    model = ConversionRequest
    template_name = 'conversions/result.html'
    context_object_name = 'conversion'
    pk_url_kwarg = 'conversion_id'
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return ConversionRequest.objects.filter(user=self.request.user)
        return ConversionRequest.objects.filter(id__in=self.request.session.get('guest_conversions', []))

class GuestResultView(DetailView):
    model = ConversionRequest
    template_name = 'conversions/result.html'
    context_object_name = 'conversion'
    pk_url_kwarg = 'conversion_id'
    def get_queryset(self):
        return ConversionRequest.objects.filter(id__in=self.request.session.get('guest_conversions', []))

class ConversionStatusView(View):
    def get(self, request, conversion_id):
        conversion = get_object_or_404(ConversionRequest, id=conversion_id)
        if conversion.user and conversion.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        return JsonResponse({
            'status': conversion.status,
            'error_message': conversion.error_message,
            'completed_at': conversion.completed_at.isoformat() if conversion.completed_at else None,
        })

class DeleteConversionView(LoginRequiredMixin, View):
    def post(self, request, conversion_id):
        conversion = get_object_or_404(ConversionRequest, id=conversion_id, user=request.user)
        if conversion.original_file: conversion.original_file.delete(save=False)
        if conversion.converted_file: conversion.converted_file.delete(save=False)
        conversion.delete()
        messages.success(request, 'Conversion deleted.')
        return redirect('conversions:history')

class RetryConversionView(LoginRequiredMixin, View):
    def post(self, request, conversion_id):
        conversion = get_object_or_404(ConversionRequest, id=conversion_id, user=request.user)
        conversion.status = 'pending'
        conversion.error_message = ""
        conversion.save()
        
        success = conversion.safe_process_conversion()
        if success:
            messages.success(request, "Retry successful!")
        else:
            messages.error(request, f"Retry failed: {conversion.error_message}")
        return redirect('conversions:history')