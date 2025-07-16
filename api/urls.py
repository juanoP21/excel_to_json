from django.urls import path
from . import views

app_name = 'excel'

urlpatterns = [
    path('convert/', views.ExcelToJsonView.as_view(), name='convert_excel'),
    path('upload/', views.ExcelUploadView.as_view(), name='upload_excel'),
]
