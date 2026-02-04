from django.urls import path
from . import views

app_name = 'letter_of_recommendation_generator'

urlpatterns = [
    path('', views.letter_dashboard, name='letter_dashboard'),
    path('create/', views.create_letter, name='create_letter'),
    path('preview/<int:pk>/', views.preview_letter, name='preview_letter'),
    path('delete/<int:pk>/', views.delete_letter, name='delete_letter'),
    path('download/pdf/<int:pk>/', views.download_letter_pdf, name='download_letter_pdf'),
    path('download/docx/<int:pk>/', views.download_letter_docx, name='download_letter_docx'),
]
