# pdfconvert/urls.py
from django.urls import path
from .views import PDFConvertView, PDFTextractView, PDFUploadView

app_name = 'pdfconvert'

urlpatterns = [
    # fijas el parámetro bank_key en la propia ruta:
path('convert/<str:bank_key>/', PDFConvertView.as_view(), name='convert_pdf'),
path('convert_textract/<str:bank_key>/', PDFTextractView.as_view(), name='convert_pdf_textract'),
path('upload/', PDFUploadView.as_view(), name='upload_pdf'),

]

