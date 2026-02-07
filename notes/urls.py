from django.urls import path
from . import views

app_name = 'notes'

urlpatterns = [
    path('', views.notes_list, name='notes_list'),
    path('generate/', views.generate_notes, name='notes'),
    path('generate-unit/<int:unit_id>/', views.generate_unit_notes, name='generate_unit_notes'),
    path('<int:note_id>/', views.note_detail, name='note_detail'),
]
