# pdfconvert/urls.py
from django.urls import path
from .views import PDFConvertView, PDFTextractView, TextractOCRView

app_name = 'pdfconvert'

urlpatterns = [
    # fijas el parámetro bank_key en la propia ruta:
path('convert/<str:bank_key>/', PDFConvertView.as_view(), name='convert_pdf'),
path('convert_textract/<str:bank_key>/', PDFTextractView.as_view(), name='convert_pdf_textract'),
path('ocr_textract/', TextractOCRView.as_view(), name='ocr_textract'),

]
