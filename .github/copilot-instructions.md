# Learnbridge AI Coding Instructions

Learnbridge is a Django-based adaptive learning platform combining AI-generated content with user activity tracking, role-based access, and Khan Academy-inspired learning structures.

## Architecture Overview

**Core Structure**: Multi-app Django project with 6 feature apps + 1 core app + Khan Academy models:
- `core/`: User authentication, roles, activity tracking, **course hierarchy (Course/Unit/Lesson), student progress tracking**
- `quiz/`: Adaptive quiz generation via Ollama LLM with mastery-based scoring
- `notes/`: Exam-oriented study notes generation
- `generator/`: Multi-day study plan creation
- `sentence_explain/`: Text/image-based explanation service
- `assessment/`: Student assessment workflows placeholder

**Key Data Flow**: 
1. User Activity Logging → All AI operations log to `UserActivity` model
2. Learning Path → Course → Unit → Lesson hierarchy
3. Progress Tracking → StudentProgress records proficiency (Not Started → Attempted → Proficient → Mastery)
4. Recommendations → Based on quiz performance and knowledge gaps

## Khan Academy-Inspired Learning Structure

### Course Hierarchy (NEW)
- **Course** (e.g., "Class 10 Math") 
  - Multiple Units (chapters)
  - Board specification (NCERT, CBSE, etc.)
  - Grade level tracking
  
- **Unit** (e.g., "Quadratic Equations")
  - Multiple Lessons (sequential)
  - Estimated hours
  - Proficiency tracking per student

- **Lesson** (individual content)
  - Title, description, HTML/Markdown content
  - Video URL support (YouTube integration)
  - Duration in minutes
  - Sequential ordering within unit

### Student Progress & Mastery System
- **StudentProgress** model tracks per-unit learning
- **Proficiency Levels** (4-tier mastery):
  - `not_started` (0%)
  - `attempted` (40-70% quiz score)
  - `proficient` (70-85% quiz score)
  - `mastery` (85%+ quiz score)
- Auto-updates based on quiz attempts and scores
- Tracks lessons completed, quiz attempts, best scores

## Critical Patterns

### Ollama AI Integration
- **Configuration**: `settings.py` defines `OLLAMA_MODEL_TEXT` ("llama3.2:1b") and `OLLAMA_MODEL_VISION` ("llava:latest")
- **Async Pattern**: All AI calls are async using `ollama.AsyncClient()` (see `quiz/ai_engine.py`, `notes/views.py`, `sentence_explain/views.py`, `generator/views.py`)
- **Sync-to-Async Bridge**: Views use `@sync_to_async` decorator to convert async operations for Django views
- **Prompt Engineering**: Use detailed format hints in prompts (Q/O/A structure for quiz, markdown headers for notes, etc.) to ensure consistent LLM output parsing

### User Profiles & Authentication
- One-to-one relationship: User → UserProfile (role: 'student' or 'teacher')
- Views use `@login_required` decorator
- Dashboard routing: Check profile.role to render different templates
- Missing profile → redirect to 'role_selection' view

### Quiz Generation (quiz/ai_engine.py)
- Unique feature: Randomized question generation using timestamp+random seeds
- Supports 5 difficulty levels: Foundation, Developing, Proficient, Advanced, Mastery
- Parser is ultra-robust—supports Q1:, Q:, Question: prefixes
- Topic-specific subtopic variation ensures question diversity
- Temperature=0.4, top_p=0.9 for controlled generation
- Integrates with StudentProgress to update proficiency levels

### Learning Path Views (core/learning_path.py) - NEW
- `explore_courses()` - Browse all available courses with student progress
- `course_detail()` - View units in course with progress per unit
- `unit_detail()` - View lessons and track unit progress
- `lesson_detail()` - Full lesson content with video/navigation
- `get_recommendations()` - AI recommendations based on quiz performance
- All views return proficiency data for visual indicators (colors, badges)

## Critical Workflows

**Run Django Development**:
```bash
python manage.py runserver
```

**Database Setup**:
```bash
python manage.py migrate
python manage.py createsuperuser
```

**Create Sample Course Data** (admin or shell):
```python
from core.models import Course, Unit, Lesson

course = Course.objects.create(
    title="Class 10 Math",
    description="NCERT Mathematics",
    board="NCERT",
    grade_level="Class 10"
)

unit = Unit.objects.create(
    course=course,
    title="Quadratic Equations",
    description="Learn quadratics",
    order=1,
    estimated_hours=5
)

lesson = Lesson.objects.create(
    unit=unit,
    title="Introduction",
    description="Basics",
    content="<p>Content</p>",
    video_url="https://youtube.com/...",
    order=1,
    duration_minutes=15
)
```

**Ollama Setup**: Ensure Ollama service is running; models must be pre-pulled:
```bash
ollama pull llama3.2:1b
ollama pull llava:latest
```

## Conventions & Gotchas

- **No URL entry point**: Root URL patterns use `include()` to namespace apps. Update `learnbridge/urls.py` when adding new app routes.
- **.env Required**: Load via `python-dotenv` (settings.py:17). Requires `SECRET_KEY` and `DEBUG` at minimum.
- **Async View Rendering**: All content-generation views are async. Use `await sync_to_async(render)()` to return templates from async contexts.
- **Empty Models**: notes/, assessment/, and generator/ models.py are intentionally empty; all logic in views.
- **Static/Media**: CSS in quiz/static/quiz/, image uploads stored in media/ directory (not gittracked).
- **Proficiency Auto-Update**: StudentProgress.update_proficiency() recalculates level based on quiz_score and quiz_attempts
- **Lesson Completion**: Track via progress.lessons_completed field (manually updated via admin/views)

## New Learning Path Routes

```
/core/
  ├── courses/              # Browse all courses
  ├── course/<id>/          # View units in course
  ├── unit/<id>/            # View lessons in unit
  ├── lesson/<id>/          # View lesson content
  ├── recommendations/      # Get AI recommendations
  └── dashboard-enhanced/   # Enhanced student dashboard
```

## File Locations by Feature

**User & Progress Management**:
- [core/models.py](../core/models.py) - UserProfile, UserActivity, **Course, Unit, Lesson, StudentProgress**
- [core/views.py](../core/views.py) - dashboard, role_selection
- [core/utils.py](../core/utils.py) - log_activity utility

**Learning Path (NEW)**:
- [core/learning_path.py](../core/learning_path.py) - 6 new views for course/unit/lesson browsing & recommendations

**Quiz AI**:
- [quiz/ai_engine.py](../quiz/ai_engine.py) - question generation with proficiency integration
- [quiz/models.py](../quiz/models.py) - QuizAttempt

**Content Generation**:
- [notes/views.py](../notes/views.py) - study notes generation
- [sentence_explain/views.py](../sentence_explain/views.py) - text + image explanation
- [generator/views.py](../generator/views.py) - 7-day study plan generation

**Configuration**:
- [learnbridge/settings.py](../learnbridge/settings.py) - Ollama models, INSTALLED_APPS, TEMPLATES
- [learnbridge/urls.py](../learnbridge/urls.py) - Root URL routing

**Admin Interface (NEW)**:
- [core/admin.py](../core/admin.py) - Course/Unit/Lesson management, StudentProgress tracking

## Templates Structure

**Root Templates** (NEW):
- [templates/base.html](../templates/base.html) - Global base template with navigation

**Core App Templates** (NEW):
- [core/templates/core/explore_courses.html](../core/templates/core/explore_courses.html) - Course browsing
- [core/templates/core/course_detail.html](../core/templates/core/course_detail.html) - Unit overview
- [core/templates/core/unit_detail.html](../core/templates/core/unit_detail.html) - Lesson list
- [core/templates/core/lesson_detail.html](../core/templates/core/lesson_detail.html) - Lesson content
- [core/templates/core/recommendations.html](../core/templates/core/recommendations.html) - AI recommendations

## Integration Points

### Quiz → Learning Progress
When QuizAttempt is created:
1. Extract topic/difficulty
2. Find related StudentProgress unit
3. Update best_quiz_score if higher
4. Call update_proficiency() to recalculate mastery level
5. Log activity via log_activity()

### Learning Recommendations
Based on:
- Units where proficiency < 'proficient' (prioritize low scores)
- Unstarted units (suggest next in sequence)
- Quiz performance trends (identify knowledge gaps)

## Key Admin Features

- Create/edit Courses with inline Unit editing
- Create/edit Units with inline Lesson editing
- Bulk view student progress across all units
- Filter by proficiency level, board, grade level
- Search by title/description
- Track last_accessed for engagement analytics
