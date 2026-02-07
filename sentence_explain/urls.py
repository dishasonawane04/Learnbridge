from django.urls import path
from . import views

app_name = 'sentence_explain'

urlpatterns = [
    path('', views.sentence_explain, name='sentence_explain'),
]
