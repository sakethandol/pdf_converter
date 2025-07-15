from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def upload_file(request):
    return render(request, 'conversions/upload.html')

@login_required
def convert_file(request):
    return render(request, 'conversions/result.html')

@login_required
def download_file(request, file_id):
    return render(request, 'conversions/download.html')

@login_required
def conversion_history(request):
    return render(request, 'conversions/history.html')