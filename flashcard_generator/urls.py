from django.urls import path
from . import views

app_name = 'flashcard_generator'

urlpatterns = [
    path('', views.flashcard_home, name='flashcard_home'),
    path('study/<int:deck_id>/', views.study_deck_view, name='study_deck'),
    path('api/generate/', views.generate_deck_api, name='generate_deck'),
    path('api/generate-task/', views.start_flashcard_deck_task, name='start_flashcard_task'),
    path('api/task-status/<str:task_id>/', views.check_flashcard_task_status, name='check_flashcard_task_status'),
    path('api/deck/<int:deck_id>/', views.get_deck_api, name='get_deck_api'),
    path('api/card/<int:card_id>/progress/', views.update_card_progress, name='update_card_progress'),
    path('api/card/<int:card_id>/explain/', views.explain_card_api, name='explain_card'),
    path('api/card/<int:card_id>/delete/', views.delete_card_api, name='delete_card_api'),
    path('api/deck/<int:deck_id>/delete/', views.delete_deck_api, name='delete_deck_api'),
    path('api/quiz/generate/<int:deck_id>/', views.generate_quiz_view, name='generate_quiz_view'),
    path('api/quiz/submit/', views.submit_quiz_api, name='submit_quiz_api'),
    path('progress/', views.progress_view, name='flashcard_progress'),
    path('api/generate_from_unit/<int:unit_id>/', views.generate_from_unit, name='generate_from_unit'),
    path('api/generate_from_course/<int:course_id>/', views.generate_from_course, name='generate_from_course'),
    path('generate-file/<int:file_id>/', views.generate_flashcards_file, name='generate_flashcards_file'),
    
    # Dynamic RAG Flashcards
    path('course/<int:course_id>/', views.dynamic_flashcards_view, name='dynamic_flashcards'),
    path('api/course/<int:course_id>/dynamic/', views.get_dynamic_flashcards_api, name='get_dynamic_flashcards_api'),
    path('api/course/<int:course_id>/regenerate/', views.regenerate_flashcards_api, name='regenerate_flashcards_api'),
]
