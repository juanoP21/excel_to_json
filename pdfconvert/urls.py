# pdfconvert/urls.py
from django.urls import path
from .views import PDFConvertView

app_name = 'pdfconvert'

urlpatterns = [
    # fijas el parámetro bank_key en la propia ruta:
path('convert/<str:bank_key>/', PDFConvertView.as_view(), name='convert_pdf'),
]
