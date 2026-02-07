from django.urls import path
from . import views

app_name = 'course'

urlpatterns = [
    path('', views.course_list, name='list'),
    path('create/', views.course_create, name='create'),
    path('<int:course_id>/', views.course_detail, name='detail'),
    path('unit/<int:unit_id>/', views.unit_detail, name='unit_detail'),
    path('<int:course_id>/unit/create/', views.unit_create, name='unit_create'),
    path('unit/<int:unit_id>/edit/', views.unit_edit, name='unit_edit'),
    path('<int:course_id>/unit/add/', views.unit_add, name='unit_add'),  # Legacy
    path('unit/<int:unit_id>/upload/', views.material_upload, name='material_upload'),
    path('unit/<int:unit_id>/chat/', views.unit_ai_chat, name='unit_ai_chat'),
    path('unit/<int:unit_id>/toggle-completion/', views.toggle_unit_completion, name='toggle_unit_completion'),
    path('api/search/', views.unit_search_api, name='search_api'),
]
