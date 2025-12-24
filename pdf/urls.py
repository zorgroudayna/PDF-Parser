from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('pdfviewer/', include('pdfviewer.urls')),  # app URLs
    path('', lambda request: redirect('pdf_index')),  # redirect root → /pdfviewer/
]
