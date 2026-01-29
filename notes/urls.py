from django.urls import path
from . import views

urlpatterns = [
    path('', views.notes_list, name='notes_list'),
    path('generate/', views.generate_notes, name='notes'),
    path('<int:note_id>/', views.note_detail, name='note_detail'),
]
