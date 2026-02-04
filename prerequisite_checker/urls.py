from django.urls import path
from . import views

app_name = 'prerequisite_checker'

urlpatterns = [
    path('', views.topic_input_view, name='home'),
    path('quiz/<int:session_id>/', views.quiz_view, name='quiz_view'),
    path('results/<int:session_id>/', views.result_view, name='result_view'),
]
