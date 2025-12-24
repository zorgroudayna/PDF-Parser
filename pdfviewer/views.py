# views.py
import os
import json
from django.shortcuts import render
from django.conf import settings
from .pdf_utils import PDFParser  # import the updated parser

def index(request):
    # Path to your PDF file in MEDIA_ROOT
    pdf_path = os.path.join(settings.MEDIA_ROOT, "Bankk.pdf")
    
    # Parse the PDF
    parser = PDFParser(pdf_path)
    pages, header_groups = parser.parse()
    
    # Pass parsed pages and header_groups to the template
    context = {
        "pages": pages,
        "header_groups": json.dumps(header_groups)  # safe JSON for JS
    }
    return render(request, "pdfviewer/index.html", context)

