from django.urls import path
from . import views

app_name = 'sentence_explain'

urlpatterns = [
    path('', views.sentence_explain, name='sentence_explain'),
    path('api/', views.sentence_explain_api, name='sentence_explain_api'),
]
