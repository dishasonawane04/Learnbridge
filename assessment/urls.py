from django.urls import path
from . import views

app_name = 'assessment'

urlpatterns = [
    path('learning-support/', views.learning_support, name='learning_support'),
    path('practice/start/<int:course_id>/', views.start_practice, name='start_practice'),
    path('practice/attempt/<int:attempt_id>/', views.attempt_practice, name='attempt_practice'),
    path('practice/submit/<int:attempt_id>/', views.submit_practice, name='submit_practice'),
    path('practice/results/<int:attempt_id>/', views.practice_results, name='practice_results'),
]
