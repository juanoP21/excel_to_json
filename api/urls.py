from django.urls import path
from . import views

urlpatterns = [
    path('convert-excel/', views.ExcelToJsonView.as_view(), name='convert-excel'),
]
