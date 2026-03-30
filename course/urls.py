from django.urls import path
from . import views

app_name = 'course'

urlpatterns = [
    path('', views.course_list, name='list'),
    path('create/', views.course_create, name='create'),
    path('<int:course_id>/', views.course_dashboard, name='course_dashboard'),
    path('<int:course_id>/dashboard/', views.course_dashboard), # Alias for convenience
    path('unit/<int:unit_id>/', views.unit_detail, name='unit_detail'),
    path('<int:course_id>/unit/create/', views.unit_create, name='unit_create'),
    path('<int:course_id>/add-lesson/', views.unit_create, name='add_lesson'),
    path('unit/<int:unit_id>/edit/', views.unit_edit, name='unit_edit'),
    path('<int:course_id>/material/upload/', views.upload_notes, name='upload_notes'),
    path('material/<int:material_id>/delete/', views.material_delete, name='material_delete'),
    path('material/<int:material_id>/rename/', views.rename_material, name='material_rename'),
    path('switch/<int:course_id>/', views.switch_course, name='switch'),
    path('research/<int:course_id>/', views.course_research, name='research'),
    path('career/<int:course_id>/', views.course_career, name='career'),
    path('summary/<int:course_id>/', views.course_summary, name='summary'),
    path('<int:course_id>/delete/', views.course_delete, name='delete'),
    path('<int:course_id>/rename/', views.course_rename, name='rename'),
    path('unit/<int:unit_id>/toggle-completion/', views.toggle_unit_completion, name='toggle_unit_completion'),
    path('unit/<int:unit_id>/chat/', views.unit_ai_chat, name='unit_ai_chat'),
    path('api/search/', views.unit_search_api, name='search_api'),
    path('api/user/courses/', views.user_courses_api, name='user_courses_api'),
    path('api/user/enrolled-courses/', views.user_courses_api, name='enrolled_courses_api'),
    path('api/set-language/', views.set_ai_language, name='set_ai_language'),
    path('api/translate/', views.translate_content, name='translate_content'),
    path('<int:course_id>/concept-map/', views.course_concept_map_api, name='concept_map_api'),
]
