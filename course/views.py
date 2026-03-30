from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse
import json
from .models import Course, CourseUnit, CourseMaterial, UserUnitCompletion, ConceptNode, UserConceptMastery, AIStudyInsight, StudyActivity
from .utils.extraction import extract_content, extract_text_from_path
from core.ai.services import ContentIntelligenceEngine, CourseContextEngine
from .services.intelligence import AIInsightService
from ai_engine.document_loader import load_document
from ai_engine.chunker import split_into_chunks
from ai_engine.vector_store import create_vector_db

@login_required
def course_list(request):
    if request.user.is_superuser or request.user.is_staff:
        courses = Course.objects.filter(is_deleted=False)
    else:
        courses = request.user.courses.filter(is_deleted=False)
    
    # Add progress data to each course
    for course in courses:
        total_units = course.units.count()
        if total_units > 0:
            completed_units = UserUnitCompletion.objects.filter(
                user=request.user, 
                unit__course=course
            ).count()
            course.progress_percentage = int((completed_units / total_units) * 100)
        else:
            course.progress_percentage = 0
            
    return render(request, 'course/course_list.html', {'courses': courses})

@login_required
def course_create(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        level = request.POST.get('level')
        course = Course.objects.create(
            user=request.user, 
            title=title, 
            description=description
        )
        
        return redirect('course:course_dashboard', course_id=course.id)
    return render(request, 'course/course_form.html')

@login_required
def course_dashboard(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    # Allow staff to view all courses, regular users only their own
    if not (request.user.is_staff or request.user.is_superuser or course.user == request.user):
        return redirect('course:list')
    
    request.session['active_course_id'] = str(course.id)
    materials = course.course_materials.all().order_by('-created_at')
    units = course.units.all().order_by('order')
    
    # Check if RAG knowledge exists
    has_knowledge = course.knowledge_chunks.exists()
    
    # Determine if any content exists (Primary file, Materials, or Units)
    has_content = materials.exists() or units.exists() or bool(course.uploaded_file)

    return render(request, 'course/course_dashboard.html', {
        'course': course,
        'materials': materials,
        'units': units,
        'has_knowledge': has_knowledge,
        'has_content': has_content
    })

@login_required
def upload_notes(request, course_id):
    course = get_object_or_404(Course, id=course_id, user=request.user)
    if request.method == "POST":
        files = request.FILES.getlist("file")
        for file in files:
            ext = file.name.split('.')[-1].lower()
            file_type = 'text'
            if ext in ['pdf']: file_type = 'pdf'
            elif ext in ['ppt', 'pptx']: file_type = 'ppt'
            elif ext in ['jpg', 'jpeg', 'png', 'webp', 'gif']: file_type = 'image'
            
            # Create the material - automated processing in models.py handles the rest (OCR, indexing)
            CourseMaterial.objects.create(
                course=course,
                file=file,
                file_type=file_type
            )
        
        # Consolidate context after all new materials are added
        from core.ai.services import CourseContextEngine
        CourseContextEngine.consolidate_course_notes(course.id)
                
    return redirect('course:course_dashboard', course_id=course.id)

@login_required
def unit_create(request, course_id):
    """Create a new unit for a course"""
    course = get_object_or_404(Course, id=course_id)
    # Only course owner or staff can create units
    if course.user != request.user and not (request.user.is_staff or request.user.is_superuser):
        return redirect('course:course_dashboard', course_id=course.id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        overview = request.POST.get('overview', '')
        content = request.POST.get('content', '')
        uploaded_file = request.FILES.get('uploaded_file')
        order = request.POST.get('order', 0)
        
        unit = CourseUnit.objects.create(
            course=course,
            title=title,
            overview=overview,
            content=content,
            uploaded_file=uploaded_file,
            order=order
        )
        
        # Auto-extract content from file if uploaded
        if unit.uploaded_file:
            try:
                extracted = extract_text_from_path(unit.uploaded_file.path)
                if extracted:
                    if unit.content:
                        unit.content += "\n\n" + extracted
                    else:
                        unit.content = extracted
                    unit.save()
            except Exception as e:
                print(f"Extraction failed: {e}")

        # Trigger Content Intelligence Engine
        ContentIntelligenceEngine.parse_unit_into_concepts(unit)
        ContentIntelligenceEngine.create_knowledge_graph(unit)
        
        return redirect('course:course_dashboard', course_id=course.id)
    
    # Calculate next order number
    max_order = course.units.aggregate(models.Max('order'))['order__max'] or 0
    next_order = max_order + 1
    
    return render(request, 'course/unit_form.html', {
        'course': course,
        'next_order': next_order
    })

@login_required
def unit_edit(request, unit_id):
    """Edit an existing unit"""
    unit = get_object_or_404(CourseUnit, id=unit_id)
    course = unit.course
    
    # Only course owner or staff can edit units
    if course.user != request.user and not (request.user.is_staff or request.user.is_superuser):
        return redirect('course:unit_detail', unit_id=unit.id)
    
    if request.method == 'POST':
        unit.title = request.POST.get('title', unit.title)
        unit.overview = request.POST.get('overview', unit.overview)
        unit.content = request.POST.get('content', unit.content)
        if request.FILES.get('uploaded_file'):
            unit.uploaded_file = request.FILES['uploaded_file']
            # Save first to get path
            unit.save()
            try:
                extracted = extract_text_from_path(unit.uploaded_file.path)
                if extracted:
                     # For edit, maybe we shouldn't overwrite, but append? 
                     # Let's append if content exists
                    unit.content = (unit.content or "") + "\n\n" + extracted
                    unit.save()
            except Exception as e:
                print(f"Extraction failed: {e}")
                
        unit.order = request.POST.get('order', unit.order)
        unit.save()
        
        # Re-trigger intelligence engine if content changed significantly
        ContentIntelligenceEngine.parse_unit_into_concepts(unit)
        ContentIntelligenceEngine.create_knowledge_graph(unit)
        
        return redirect('course:unit_detail', unit_id=unit.id)
    
    return render(request, 'course/unit_form.html', {
        'course': course,
        'unit': unit,
        'is_edit': True
    })

# Legacy alias for backward compatibility
@login_required
def unit_add(request, course_id):
    """Legacy endpoint - redirects to unit_create"""
    return unit_create(request, course_id)

@login_required
def material_upload_direct(request, course_id):
    """Direct upload to course (New Workflow)"""
    course = get_object_or_404(Course, id=course_id, user=request.user)
    if request.method == 'POST' and request.FILES.get('file'):
        file_obj = request.FILES['file']
        ext = file_obj.name.split('.')[-1].lower()
        
        file_type = 'text'
        if ext in ['pdf']: file_type = 'pdf'
        elif ext in ['ppt', 'pptx']: file_type = 'ppt'
        elif ext in ['jpg', 'jpeg', 'png', 'webp']: file_type = 'image'
        
        if file_obj:
            # Create the material - automated processing in models.py handles the rest
            CourseMaterial.objects.create(
                course=course,
                file=file_obj,
                file_type=file_type
            )
            
        return redirect('course:course_dashboard', course_id=course.id)
    return redirect('course:course_dashboard', course_id=course.id)

@login_required
def material_delete(request, material_id):
    material = get_object_or_404(CourseMaterial, id=material_id, course__user=request.user)
    course_id = material.course.id
    material.file.delete(save=False)
    material.delete()
    # Re-consolidate after deletion
    CourseContextEngine.consolidate_course_notes(course_id)
    return redirect('course:course_dashboard', course_id=course_id)

@login_required
def rename_material(request, material_id):
    """Rename a document display name via AJAX POST."""
    material = get_object_or_404(CourseMaterial, id=material_id, course__user=request.user)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_name = data.get('name', '').strip()
            if not new_name:
                return JsonResponse({'status': 'error', 'message': 'Name cannot be empty.'}, status=400)
            material.display_name = new_name
            material.save(update_fields=['display_name'])
            return JsonResponse({'status': 'success', 'name': new_name})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'POST required.'}, status=405)


@login_required
def material_upload(request, unit_id):
    """Legacy upload to unit"""
    unit = get_object_or_404(CourseUnit, id=unit_id, course__user=request.user)

@login_required
def unit_detail(request, unit_id):
    """
    The Central Hub View.
    Displays Notes and links to other apps.
    """
    unit = get_object_or_404(CourseUnit, id=unit_id)
    
    # Ensure user owns the course
    if unit.course.user != request.user and not (request.user.is_staff or request.user.is_superuser):
        return redirect('course:list')

    # Get All units for sidebar
    all_units = unit.course.units.all()
    completed_unit_ids = UserUnitCompletion.objects.filter(
        user=request.user, 
        unit__course=unit.course
    ).values_list('unit_id', flat=True)

    # Get Previous and Next units for navigation
    previous_unit = CourseUnit.objects.filter(course=unit.course, order__lt=unit.order).order_by('-order').first()
    next_unit = CourseUnit.objects.filter(course=unit.course, order__gt=unit.order).order_by('order').first()

    is_completed = unit.id in completed_unit_ids

    # AI Intelligence Layer
    AIInsightService.track_activity(request.user, unit.course, 'unit_view', points=10)
    unit_insights = AIInsightService.get_unit_insights(request.user, unit)

    # Knowledge Layer Data
    concepts = unit.concepts.all().order_by('order')
    
    # Initialize Mastery for this user if not existing
    mastery_data = []
    for concept in concepts:
        mastery, _ = UserConceptMastery.objects.get_or_create(
            user=request.user, 
            concept=concept
        )
        # Mock some progress for demonstration if score is 0
        if mastery.score == 0:
            import random
            mastery.score = random.randint(30, 95)
            mastery.save()
        mastery_data.append(mastery)

    context = {
        'unit': unit,
        'all_units': all_units,
        'completed_unit_ids': completed_unit_ids,
        'previous_unit': previous_unit,
        'next_unit': next_unit,
        'is_completed': is_completed,
        'concepts': concepts,
        'mastery_data': mastery_data,
        'unit_mastery': unit_insights['mastery'],
        'weak_concepts': unit_insights['weak_concepts']
    }
    return render(request, 'course/unit_detail.html', context)
@login_required
def toggle_unit_completion(request, unit_id):
    unit = get_object_or_404(CourseUnit, id=unit_id)
    completion, created = UserUnitCompletion.objects.get_or_create(user=request.user, unit=unit)
    
    if not created:
        completion.delete()
        status = 'not_completed'
    else:
        status = 'completed'
        
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': status})
    
    return redirect('course:unit_detail', unit_id=unit.id)

@login_required
def unit_ai_chat(request, unit_id):
    """
    API Endpoint for the Unit AI Assistant.
    Expects JSON POST with 'message'.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message')
            
            unit = get_object_or_404(CourseUnit, id=unit_id)
            course = unit.course
            
            # Security check
            if course.user != request.user:
                return JsonResponse({'error': 'Unauthorized'}, status=403)
                
            # --- CENTRALIZED AI QUERY ---
            ai_response = CourseContextEngine.ask_course_ai(course.id, user_message)
            
            return JsonResponse({'response': ai_response})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def unit_search_api(request):
    """API for the Ctrl+K Navigator"""
    query = request.GET.get('q', '').lower()
    
    # Get units from all courses the user is enrolled in
    units = CourseUnit.objects.filter(
        models.Q(course__user=request.user) | 
        models.Q(course__user__is_staff=True)
    ).filter(
        models.Q(title__icontains=query) | 
        models.Q(overview__icontains=query)
    ).select_related('course')[:10]
    
    results = []
    for u in units:
        results.append({
            'id': u.id,
            'title': u.title,
            'course': u.course.title,
            'url': f"/course/unit/{u.id}/"
        })
        
@login_required
def switch_course(request, course_id):
    # View to explicitly switch the active course context
    from .services.state import ActiveCourseManager
    course = ActiveCourseManager.set_active_course(request, course_id)
    return redirect('course:course_dashboard', course_id=course.id)
    referer = request.META.get('HTTP_REFERER')
    if referer and 'course/' in referer:
        return redirect('course:course_dashboard', course_id=course_id)
    return redirect('course:list')

@login_required
def course_research(request, course_id):
    """Generates research topics and project ideas based on course content."""
    course = get_object_or_404(Course, id=course_id)
    prompt = (
        "Based on the course content, suggest 5 high-impact research topics "
        "and 3 hands-on project ideas that would help a student master this subject. "
        "Format as clear bullet points with brief explanations."
    )
    content = CourseContextEngine.ask_course_ai(course.id, prompt)
    return render(request, 'course/ai_tool_result.html', {
        'course': course,
        'tool_name': 'Research & Projects',
        'content': content,
        'icon': 'fa-microscope'
    })

@login_required
def course_career(request, course_id):
    """Generates a career roadmap and skill gap analysis."""
    course = get_object_or_404(Course, id=course_id)
    prompt = (
        "Analyze the skills/knowledge covered in this course material. "
        "1. List 5 potential job roles this knowledge applies to. "
        "2. Provide a 3-step 'Next Level' roadmap for a student to enter this industry. "
        "3. Identify 3 complementary skills to learn next."
    )
    content = CourseContextEngine.ask_course_ai(course.id, prompt)
    return render(request, 'course/ai_tool_result.html', {
        'course': course,
        'tool_name': 'Career Roadmap',
        'content': content,
        'icon': 'fa-map-signs'
    })

@login_required
def course_summary(request, course_id):
    """Generates a comprehensive executive summary of the entire course material."""
    course = get_object_or_404(Course, id=course_id)
    language = request.POST.get("language", "English")
    
    # Return cached summary if available - CLEARING ONCE TO RE-FORMAT
    if course.executive_summary:
        # Check if it has markdown, if so, clear it once
        if '#' in course.executive_summary or '*' in course.executive_summary:
             course.executive_summary = ""
             course.save(update_fields=['executive_summary'])
        else:
            return render(request, 'course/ai_tool_result.html', {
                'course': course,
                'tool_name': 'Course Summary Engine',
                'content': course.executive_summary,
                'icon': 'fa-file-invoice',
                'is_error': False
            })
        
    prompt = (
        f"Synthesize all provided course material into a clean textbook-style Executive Summary in {language}. "
        "Cover Major Concepts, Core Objectives, and Critical Takeaways. "
        "\nSTRICT REQUIREMENTS: "
        "1. Output must be PLAIN ACADEMIC TEXT only. "
        "2. Use ONLY paragraphs. No bullet points or symbols. "
        "3. ABSOLUTELY NO markdown: No #, no *, no _, no bold, no italic. "
        "4. Use simple, clear language with logical organization. "
        "5. If listing items, use normal sentences starting with 'First,', 'Second,', etc. or simple numbers (1, 2, 3). "
        f"Ensure the response is strictly in {language}."
    )
    content = CourseContextEngine.ask_course_ai(course.id, prompt, specialized_mode='summary')
    
    # --- ROBUST TEXT CLEANING (Strip all markdown/symbols) ---
    import re
    # Remove #, *, _, `, and other common markdown symbols
    content = re.sub(r'[#*_`~>|+]', '', content)
    # Remove bullet symbols (•, -, +, *) at the start of lines or middle
    content = re.sub(r'^[ \t]*[-+*•][ \t]+', '', content, flags=re.MULTILINE)
    # Ensure paragraphs are clean
    content = re.sub(r'\n{3,}', '\n\n', content).strip()
    
    is_error = "Error contacting AI service" in content or content.startswith("Error:")
    
    # Cache the result if successful
    if not is_error:
        course.executive_summary = content
        course.save(update_fields=['executive_summary'])
        
    return render(request, 'course/ai_tool_result.html', {
        'course': course,
        'tool_name': 'Course Summary Engine',
        'content': content,
        'icon': 'fa-file-invoice',
        'is_error': is_error
    })
@login_required
def course_rename(request, course_id):
    """Rename a course via AJAX"""
    course = get_object_or_404(Course, id=course_id)
    
    # Ownership verification
    if course.user != request.user and not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_title = data.get('title', '').strip()
            
            if not new_title:
                return JsonResponse({'status': 'error', 'message': 'Title cannot be empty'}, status=400)
                
            course.title = new_title
            course.save(update_fields=['title'])
            
            return JsonResponse({'status': 'success', 'message': 'Course renamed successfully', 'new_title': new_title})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@login_required
def course_delete(request, course_id):
    """Securely soft-delete a course and all its data"""
    course = get_object_or_404(Course, id=course_id)
    
    # Ownership verification
    if course.user != request.user and not (request.user.is_staff or request.user.is_superuser):
        return redirect('course:list')
    
    title = course.title
    # Soft Delete
    course.is_deleted = True
    course.is_active = False
    course.save()
    
    # Reset active course in session if it was the one deleted
    if request.session.get('active_course_id') == str(course_id):
        request.session['active_course_id'] = None
    
    from django.contrib import messages
    messages.success(request, f"Course '{title}' has been successfully removed.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse({'status': 'success', 'message': f"Course '{title}' deleted."})
        
    return redirect('course:list')

@login_required
def user_courses_api(request):
    """Returns dynamic list of courses for the active user"""
    if request.user.is_staff or request.user.is_superuser:
        courses = Course.objects.filter(is_deleted=False)
    else:
        courses = Course.objects.filter(user=request.user, is_deleted=False)
    
    data = []
    for c in courses.order_by('title'):
        data.append({
            'id': c.id,
            'title': c.title,
            'level': c.get_level_display(),
            'url': f"/course/{c.id}/"
        })
    return JsonResponse({'status': 'success', 'courses': data})

@login_required
def course_concept_map_api(request, course_id):
    """Returns the concept map data for a course."""
    from .services.concept_map import ConceptMapService
    from .models import ConceptMap
    
    course = get_object_or_404(Course, id=course_id)
    if not (request.user.is_staff or request.user.is_superuser or course.user == request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    force = request.GET.get('force') == '1'
    concept_map = None
    error_msg = 'No notes available to generate concept map.'
    
    if not force:
        concept_map = ConceptMap.objects.filter(course=course, user=request.user).first()
    
    # If it doesn't exist or we are forcing an update, try to generate it
    if not concept_map:
        concept_map, error_msg = ConceptMapService.generate_for_course(course_id, request.user)
        
    if concept_map:
        return JsonResponse({'status': 'success', 'data': concept_map.data})
    
    return JsonResponse({'status': 'empty', 'message': error_msg})

@login_required
def set_ai_language(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lang = data.get('language', 'English')
            request.session['ai_language'] = lang
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def translate_content(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            text = data.get('text', '')
            if not text:
                return JsonResponse({'status': 'error', 'message': 'No text provided'}, status=400)
                
            lang = request.session.get('ai_language', 'English')
            if lang.lower() == 'english':
                return JsonResponse({'status': 'success', 'translated_text': text})
                
            prompt = f"Translate the following educational content completely and accurately into {lang}. Preserve all formatting, line breaks, emojis, and styling exactly as provided.\n\nContent to translate:\n{text}"
            translated = CourseContextEngine.ask_course_ai_raw(prompt)
            
            return JsonResponse({'status': 'success', 'translated_text': translated})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=400)

