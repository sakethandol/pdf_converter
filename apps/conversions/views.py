from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponse, Http404, FileResponse, JsonResponse
from django.views.generic import FormView, DetailView, ListView, TemplateView, View
from django.urls import reverse_lazy
from django.utils.encoding import smart_str
from django.conf import settings
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
import os
import mimetypes
from .models import ConversionRequest
from .forms import FileUploadForm

class FileUploadView(LoginRequiredMixin, FormView):
    """File upload view for authenticated users"""
    template_name = 'conversions/upload.html'
    form_class = FileUploadForm
    login_url = '/login/'
    
    def get(self, request, *args, **kwargs):
        print(f"FileUploadView GET - User: {request.user}")
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        print(f"FileUploadView POST - User: {request.user}")
        print(f"POST data: {request.POST}")
        print(f"FILES data: {request.FILES}")
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        try:
            print(f"🚀 Form is valid, processing for user: {self.request.user}")
            
            # ✅ STEP 1: Create conversion object but don't save yet
            conversion = form.save(commit=False)
            
            # ✅ STEP 2: Assign user FIRST and verify
            conversion.user = self.request.user
            print(f"🔒 User assigned: {conversion.user} (ID: {conversion.user.id})")
            
            # ✅ STEP 3: Set file metadata
            if 'original_file' not in self.request.FILES:
                raise KeyError("No file uploaded")
                
            conversion.original_filename = self.request.FILES['original_file'].name
            conversion.file_size = self.request.FILES['original_file'].size
            
            # ✅ STEP 4: Save with user explicitly set
            conversion.save()
            print(f"💾 Conversion saved with ID: {conversion.id}, User: {conversion.user}")
            
            # ✅ STEP 5: Verify user is still there
            conversion.refresh_from_db()
            if conversion.user != self.request.user:
                raise Exception(f"❌ User lost after save! Expected: {self.request.user}, Got: {conversion.user}")
            
            # ✅ STEP 6: Use the safer conversion method
            success = conversion.safe_process_conversion()
            
            # ✅ STEP 7: Final verification
            conversion.refresh_from_db()
            print(f"🏁 Final state - User: {conversion.user}, Status: {conversion.status}")
            
            if conversion.user != self.request.user:
                # Emergency fix
                ConversionRequest.objects.filter(id=conversion.id).update(user=self.request.user)
                print(f"🆘 Emergency user restoration applied")
            
            if success:
                messages.success(self.request, 'File uploaded and converted successfully!')
            else:
                messages.warning(self.request, 'File uploaded but conversion failed. Please try again.')
                
            return redirect('conversions:convert_detail', conversion_id=conversion.id)
            
        except KeyError as e:
            print(f"❌ KeyError: {e}")
            messages.error(self.request, 'Please select a file to upload.')
            return self.form_invalid(form)
        except Exception as e:
            print(f"❌ Exception in form_valid: {e}")
            messages.error(self.request, f'Error processing file: {str(e)}')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        print("=== FORM INVALID DEBUG ===")
        print(f"Form errors: {form.errors}")
        print(f"Form data: {form.data}")
        print(f"Form files: {form.files}")
        print(f"Request POST: {self.request.POST}")
        print(f"Request FILES: {self.request.FILES}")
        print(f"Form fields: {list(form.fields.keys())}")
        
        for field_name, field in form.fields.items():
            field_value = form.data.get(field_name) if hasattr(form, 'data') else None
            print(f"Field {field_name}: value='{field_value}', required={field.required}")
        
        print("=== END DEBUG ===")
        
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get the 5 most recent conversions
        context['recent_conversions'] = ConversionRequest.objects.filter(
            user=self.request.user
        ).order_by('-created_at')[:5]
        return context


class GuestConvertView(FormView):
    """File conversion view for guest users"""
    template_name = 'conversions/upload.html'
    form_class = FileUploadForm
    
    def form_valid(self, form):
        try:
            print(f"🎭 Guest conversion starting")
            conversion = form.save(commit=False)
            conversion.user = None  # Explicitly set to None for guests
            conversion.original_filename = self.request.FILES['original_file'].name
            conversion.file_size = self.request.FILES['original_file'].size
            conversion.save()
            
            print(f"💾 Guest conversion saved with ID: {conversion.id}")
            
            # Use the safer conversion method for guests too
            success = conversion.safe_process_conversion()
            
            if 'guest_conversions' not in self.request.session:
                self.request.session['guest_conversions'] = []
            self.request.session['guest_conversions'].append(conversion.id)
            self.request.session.modified = True
            
            if success:
                messages.success(self.request, 'File uploaded and converted successfully!')
            else:
                messages.warning(self.request, 'File uploaded but conversion failed. Please try again.')
            
            return redirect('conversions:guest_result', conversion_id=conversion.id)
        except Exception as e:
            print(f"❌ Guest conversion error: {e}")
            messages.error(self.request, f'Error processing file: {str(e)}')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        print("Guest form errors:", form.errors)
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class ConversionDetailView(LoginRequiredMixin, DetailView):
    model = ConversionRequest
    template_name = 'conversions/result.html'
    context_object_name = 'conversion'
    pk_url_kwarg = 'conversion_id'
    login_url = '/login/'
    
    def get_queryset(self):
        return ConversionRequest.objects.filter(user=self.request.user)


class GuestResultView(DetailView):
    model = ConversionRequest
    template_name = 'conversions/result.html'
    context_object_name = 'conversion'
    pk_url_kwarg = 'conversion_id'
    
    def get_queryset(self):
        if 'guest_conversions' in self.request.session:
            return ConversionRequest.objects.filter(
                id__in=self.request.session['guest_conversions']
            )
        return ConversionRequest.objects.none()


class ConversionHistoryView(LoginRequiredMixin, ListView):
    """Enhanced conversion history view with statistics and detailed context"""
    model = ConversionRequest
    template_name = 'conversions/history.html'
    context_object_name = 'conversions'
    login_url = '/login/'
    paginate_by = 10
    
    def get_queryset(self):
        return ConversionRequest.objects.filter(user=self.request.user).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get user's conversions for statistics
        user_conversions = ConversionRequest.objects.filter(user=self.request.user)
        
        # Calculate comprehensive statistics
        context.update({
            # Basic counts
            'total_conversions': user_conversions.count(),
            'completed_conversions': user_conversions.filter(status='completed').count(),
            'failed_conversions': user_conversions.filter(status='failed').count(),
            'processing_conversions': user_conversions.filter(status='processing').count(),
            'pending_conversions': user_conversions.filter(status='pending').count(),
            
            # Additional useful stats
            'total_downloads': sum([conv.download_count for conv in user_conversions]),
            'recent_activity': user_conversions.filter(created_at__gte=timezone.now() - timedelta(days=7)).count(),
            
            # Conversion type breakdown
            'pdf_to_word_count': user_conversions.filter(conversion_type='pdf_to_word').count(),
            'word_to_pdf_count': user_conversions.filter(conversion_type='word_to_pdf').count(),
            'pdf_to_excel_count': user_conversions.filter(conversion_type='pdf_to_excel').count(),
            'excel_to_pdf_count': user_conversions.filter(conversion_type='excel_to_pdf').count(),
            'pdf_to_image_count': user_conversions.filter(conversion_type='pdf_to_image').count(),
            'image_to_pdf_count': user_conversions.filter(conversion_type='image_to_pdf').count(),
            
            # Success rate
            'success_rate': round((user_conversions.filter(status='completed').count() / user_conversions.count() * 100) if user_conversions.count() > 0 else 0, 1),
        })
        
        return context


class FileDownloadView(LoginRequiredMixin, View):
    login_url = '/login/'
    
    def get(self, request, file_id):
        print(f"=== DOWNLOAD DEBUG ===")
        print(f"Looking for conversion ID: {file_id} for user: {request.user}")
        
        try:
            conversion = ConversionRequest.objects.get(id=file_id, user=request.user)
        except ConversionRequest.DoesNotExist:
            try:
                conversion = ConversionRequest.objects.get(id=file_id, user=None)
                if 'guest_conversions' not in request.session:
                    request.session['guest_conversions'] = []
                if file_id not in request.session['guest_conversions']:
                    request.session['guest_conversions'].append(file_id)
                    request.session.modified = True
            except ConversionRequest.DoesNotExist:
                messages.error(request, 'File not found.')
                return redirect('conversions:history')
        
        print(f"Found conversion: {conversion}")
        print(f"Conversion status: {conversion.status}")
        print(f"Has converted file: {bool(conversion.converted_file)}")
        
        if conversion.status != 'completed':
            print(f"Conversion status is: {conversion.status}")
            if conversion.status == 'failed':
                messages.error(request, f'File conversion failed: {conversion.error_message}')
            else:
                messages.error(request, f'File conversion is {conversion.status}. Please wait.')
            return redirect('conversions:history')
        
        if not conversion.converted_file:
            print("No converted file found")
            messages.error(request, 'Converted file not found.')
            return redirect('conversions:history')
        
        try:
            file_path = conversion.converted_file.path
        except ValueError:
            # Handle case where file is missing from storage
            file_path = os.path.join(
                settings.MEDIA_ROOT, 
                conversion.converted_file.name
            )
        
        if not os.path.exists(file_path):
            print(f"File does not exist at: {file_path}")
            messages.error(request, 'File not found on server.')
            return redirect('conversions:history')
        
        conversion.user = self.request.user  # Re-assign before save
        conversion.save()
        
        try:
            filename = conversion.converted_filename or f"converted_{conversion.original_filename}"
            print(f"Serving file: {filename}")
            
            response = FileResponse(
                open(file_path, 'rb'),
                as_attachment=True,
                filename=filename
            )
            print(f"File served successfully")
            return response
        except Exception as e:
            print(f"File serving error: {e}")
            messages.error(request, f'Error downloading file: {str(e)}')
            return redirect('conversions:history')


class GuestDownloadView(View):
    def get(self, request, file_id):
        if 'guest_conversions' not in request.session or file_id not in request.session['guest_conversions']:
            messages.error(request, 'You do not have permission to download this file.')
            return redirect('/')
        
        conversion = get_object_or_404(
            ConversionRequest, 
            id=file_id, 
            user=None,
            status='completed'
        )
        
        try:
            file_path = conversion.converted_file.path
        except ValueError:
            # Handle case where file is missing from storage
            file_path = os.path.join(
                settings.MEDIA_ROOT, 
                conversion.converted_file.name
            )
        
        if not os.path.exists(file_path):
            messages.error(request, 'File not found on server.')
            return redirect('conversions:guest_result', conversion_id=conversion.id)
        
        conversion.download_count += 1
        conversion.save()
        
        filename = conversion.converted_filename or f"converted_{conversion.original_filename}"
        
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


class ConversionStatusView(View):
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
                    if 'guest_conversions' in request.session and conversion_id in request.session['guest_conversions']:
                        conversion = get_object_or_404(
                            ConversionRequest, 
                            id=conversion_id, 
                            user=None
                        )
                    else:
                        return JsonResponse({'error': 'Conversion not found'}, status=404)
                
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
    login_url = '/login/'
    
    def post(self, request, conversion_id):
        conversion = get_object_or_404(
            ConversionRequest, 
            id=conversion_id, 
            user=request.user
        )
        
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
        
        conversion.delete()
        messages.success(request, 'Conversion deleted successfully.')
        
        return redirect('conversions:history')
    
    def get(self, request, conversion_id):
        return redirect('conversions:history')