from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse
import json
from .models import Course, CourseUnit, CourseMaterial, UserUnitCompletion, ConceptNode, UserConceptMastery, AIStudyInsight, StudyActivity
from .utils.extraction import extract_content, extract_text_from_path
from core.ai.services import ContentIntelligenceEngine
from .services.ai_context import get_system_prompt, query_ai_service
from .services.intelligence import AIInsightService

@login_required
def course_list(request):
    if request.user.is_superuser or request.user.is_staff:
        courses = Course.objects.all()
    else:
        courses = request.user.courses.all()
    
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
            description=description, 
            level=level
        )
        
        # Check for initial file upload
        if request.FILES.get('course_file'):
            try:
                uploaded_file = request.FILES['course_file']
                # Create initial unit
                unit = CourseUnit.objects.create(
                    course=course,
                    title="Course Introduction & Materials",
                    overview="Initial materials uploaded during course creation.",
                    uploaded_file=uploaded_file,
                    order=1
                )
                
                # Extract text
                extracted = extract_text_from_path(unit.uploaded_file.path)
                if extracted:
                    unit.content = extracted
                    unit.save()
                    
                    # Intelligence Analysis
                    ContentIntelligenceEngine.parse_unit_into_concepts(unit)
                    ContentIntelligenceEngine.create_knowledge_graph(unit)
            except Exception as e:
                print(f"Initial course file processing failed: {e}")

        return redirect('course:detail', course_id=course.id)
    return render(request, 'course/course_form.html')

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    # Allow staff to view all courses, regular users only their own
    if not (request.user.is_staff or request.user.is_superuser or course.user == request.user):
        return redirect('course:list')
    
    # Progress calculation
    units = course.units.all()
    total_units = units.count()
    completed_unit_ids = UserUnitCompletion.objects.filter(
        user=request.user, 
        unit__course=course
    ).values_list('unit_id', flat=True)
    
    if total_units > 0:
        progress_percentage = int((len(completed_unit_ids) / total_units) * 100)
    else:
        progress_percentage = 0

    # AI Intelligence Layer
    AIInsightService.track_activity(request.user, course, 'course_view', points=5)
    readiness = AIInsightService.calculate_course_readiness(request.user, course)
    estimated_time = AIInsightService.estimate_completion_time(course)
    heatmap_data = AIInsightService.get_heatmap_data(request.user, course)
    daily_insight = AIInsightService.generate_daily_insight(request.user, course)
    
    # Enrich units with AI mastery data for roadmap
    for unit in units:
        insights = AIInsightService.get_unit_insights(request.user, unit)
        unit.ai_mastery = insights['mastery']
        unit.is_weak = len(insights['weak_concepts']) > 0

    return render(request, 'course/course_detail.html', {
        'course': course,
        'units': units,
        'completed_unit_ids': completed_unit_ids,
        'progress_percentage': progress_percentage,
        'readiness': readiness,
        'estimated_time': estimated_time,
        'heatmap_data': heatmap_data,
        'daily_insight': daily_insight
    })

@login_required
def unit_create(request, course_id):
    """Create a new unit for a course"""
    course = get_object_or_404(Course, id=course_id)
    # Only course owner or staff can create units
    if course.user != request.user and not (request.user.is_staff or request.user.is_superuser):
        return redirect('course:detail', course_id=course.id)
    
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
        
        return redirect('course:detail', course_id=course.id)
    
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
def material_upload(request, unit_id):
    unit = get_object_or_404(CourseUnit, id=unit_id, course__user=request.user)
    if request.method == 'POST' and request.FILES.get('file'):
        material = CourseMaterial.objects.create(
            unit=unit,
            file=request.FILES['file']
        )
        # Process file automatically for general text
        extract_content(material)
        
        # Trigger structural analysis from extracted text
        ContentIntelligenceEngine.parse_unit_into_concepts(unit, content_text=material.extracted_text)
        ContentIntelligenceEngine.create_knowledge_graph(unit)
        
        return redirect('course:detail', course_id=unit.course.id)
    return redirect('course:detail', course_id=unit.course.id)

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
                
            system_prompt = get_system_prompt(course, unit)
            ai_response = query_ai_service(user_message, system_prompt)
            
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
        
    return JsonResponse({'results': results})
