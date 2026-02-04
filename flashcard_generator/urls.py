from django.urls import path
from . import views

urlpatterns = [
    path('', views.flashcard_home, name='flashcard_home'),
    path('study/<int:deck_id>/', views.study_deck_view, name='study_deck'),
    path('api/generate/', views.generate_deck_api, name='generate_deck'),
    path('api/generate/', views.generate_deck_api, name='generate_deck_api'),
    path('api/deck/<int:deck_id>/', views.get_deck_api, name='get_deck_api'),
    path('api/card/<int:card_id>/progress/', views.update_card_progress, name='update_card_progress'),
    path('api/card/<int:card_id>/explain/', views.explain_card_api, name='explain_card'),
    path('api/card/<int:card_id>/delete/', views.delete_card_api, name='delete_card_api'),
    path('api/deck/<int:deck_id>/delete/', views.delete_deck_api, name='delete_deck_api'),
    path('api/quiz/submit/', views.submit_quiz_api, name='submit_quiz_api'),
    path('progress/', views.progress_view, name='flashcard_progress'),
]
