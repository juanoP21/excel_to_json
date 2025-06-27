from django.urls import path
from .views import TextractOCRView

app_name = 'ocr'

urlpatterns = [
    path('textract/', TextractOCRView.as_view(), name='textract'),
]
