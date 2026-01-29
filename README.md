# 📚 Learnbridge - Adaptive Learning Platform

[![Django 4.2](https://img.shields.io/badge/Django-4.2-green.svg)](https://www.djangoproject.com/)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An AI-powered adaptive learning platform inspired by Khan Academy, combining structured course hierarchies with intelligent quiz generation, progress tracking, and personalized learning recommendations.

## 🎯 Features

### Core Learning Features
- 📚 **Course Hierarchy** - Organize content into courses → units → lessons
- 🎓 **Proficiency Tracking** - 4-level mastery system (Not Started → Mastery)
- 🤖 **AI Quiz Generation** - Adaptive quizzes powered by Ollama LLM
- 📊 **Progress Analytics** - Real-time learning metrics and dashboards
- 💡 **Smart Recommendations** - Personalized learning paths based on performance
- 🎥 **Multimedia Support** - Embedded videos, markdown content, interactive lessons

### Teacher/Admin Tools
- ➕ **Content Management** - Create and manage courses, units, lessons
- 📈 **Student Analytics** - Track class progress and individual performance
- 🔍 **Performance Insights** - Identify struggling students automatically
- ⚙️ **Flexible Configuration** - Multi-board support (NCERT, CBSE, etc.)

### AI-Powered Features
- 🤖 **Intelligent Quiz Generation** - Randomized questions with topic variation
- 📝 **Study Notes Generation** - Auto-generated exam-oriented notes
- 💬 **Sentence Explanation** - Break down complex concepts
- 📅 **Study Plan Generation** - 7-day personalized study plans

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Django 4.2+
- Ollama (for AI features)
- Virtual environment

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd Learnbridge
```

2. **Create and activate virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Setup environment variables**
```bash
cp .env.example .env
# Edit .env with your SECRET_KEY and settings
```

5. **Run migrations**
```bash
python manage.py migrate
```

6. **Create superuser**
```bash
python manage.py createsuperuser
```

7. **Start Ollama service** (for AI features)
```bash
ollama serve
# In another terminal:
ollama pull llama3.2:1b
ollama pull llava:latest
```

8. **Run development server**
```bash
python manage.py runserver
```

Visit: http://localhost:8000/

## 📖 Usage

### For Students

1. **Browse Courses** → `/core/courses/`
   - See all available courses
   - Track your progress

2. **Study Content** → `/core/course/<id>/` → `/core/lesson/<id>/`
   - Watch videos
   - Read lessons
   - Complete all lessons in a unit

3. **Take Quizzes** → `/`
   - Test your knowledge
   - Your scores automatically update proficiency levels

4. **Get Recommendations** → `/core/recommendations/`
   - AI-powered personalized learning path
   - Identify weak areas
   - Plan next topics

### For Teachers/Admins

1. **Create Courses** → `/admin/core/course/add/`
2. **Add Units** → `/admin/core/unit/add/`
3. **Create Lessons** → `/admin/core/lesson/add/`
4. **Track Students** → `/admin/core/studentprogress/`
5. **View Analytics** → `/admin/`

## 🏗️ Architecture

### Technology Stack
- **Backend**: Django 4.2 (Python)
- **Database**: SQLite (development), PostgreSQL (production)
- **AI Engine**: Ollama (llama3.2:1b, llava)
- **Frontend**: Bootstrap 4, HTML5, CSS3
- **Async**: AsyncIO with `asgiref`

### Key Components

```
┌─────────────────────────────────────┐
│        Student Dashboard            │
├─────────────────────────────────────┤
│  Course → Unit → Lesson Structure   │
│         Progress Tracking           │
│     Proficiency Levels (4-tier)     │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│       Quiz & Assessment System      │
│   (AI-Powered via Ollama LLM)       │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│  Recommendations Engine             │
│  (Personalized Learning Paths)      │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│  Admin Dashboard & Analytics        │
│  (Content Management & Reporting)   │
└─────────────────────────────────────┘
```

### Database Schema

**Course** → **Unit** → **Lesson**
- Hierarchical organization
- Multiple boards (NCERT, CBSE)
- Grade level tracking

**StudentProgress**
- Per-unit tracking
- Proficiency levels
- Quiz scores
- Lesson completion

**UserActivity**
- All learning events logged
- Time tracking
- Outcome recording

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Step-by-step setup and usage guide
- **[KHAN_ACADEMY_IMPLEMENTATION.md](KHAN_ACADEMY_IMPLEMENTATION.md)** - Detailed feature specification
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Complete implementation details
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** - AI agent guidelines

## 🎓 Learning Path Example

```
Student
  ↓
Explore Courses (/core/courses/)
  ↓
Select Course → View Units
  ↓
Complete Lessons → Watch Videos
  ↓
Take Quiz → Score Updates Proficiency
  ↓
Get Recommendations (/core/recommendations/)
  ↓
Continue Learning or Review Weak Areas
```

## 📊 Proficiency Levels

| Level | Score | Color |
|-------|-------|-------|
| **Not Started** | 0% | Gray |
| **Attempted** | 40-70% | Yellow |
| **Proficient** | 70-85% | Blue |
| **Mastery** | 85%+ | Green |

## 🔗 URL Routes

| Route | Purpose |
|-------|---------|
| `/` | Quiz home |
| `/core/courses/` | Browse courses |
| `/core/course/<id>/` | View units |
| `/core/unit/<id>/` | View lessons |
| `/core/lesson/<id>/` | Learn lesson |
| `/core/recommendations/` | Get suggestions |
| `/admin/` | Admin panel |

## 🛠️ Configuration

### settings.py
```python
# Ollama AI Models
OLLAMA_MODEL_TEXT = "llama3.2:1b"
OLLAMA_MODEL_VISION = "llava:latest"

# Learning Platform
INSTALLED_APPS = [
    'core',      # User auth, courses, progress
    'quiz',      # Quiz generation
    'notes',     # Study notes
    'generator', # Study plans
    'sentence_explain',  # Explanations
    'assessment',  # Assessment workflows
]
```

## 🧪 Testing

### Create Sample Data
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
    description="Master quadratic equations",
    order=1,
    estimated_hours=5
)

lesson = Lesson.objects.create(
    unit=unit,
    title="Introduction",
    description="Basics of quadratic equations",
    content="<h2>Quadratic Equations</h2><p>...</p>",
    video_url="https://youtube.com/embed/...",
    order=1,
    duration_minutes=15
)
```

## 🔐 Security

- User authentication and authorization
- Role-based access (Student/Teacher)
- CSRF protection
- SQL injection prevention via ORM
- Environment variables for secrets

## 📈 Analytics

Track:
- Student enrollment by course
- Unit completion rates
- Proficiency distribution
- Quiz attempt trends
- Time-on-task metrics
- Knowledge gap patterns

## 🐛 Troubleshooting

### Issue: Can't see courses
**Solution**: Make sure courses are created in admin panel

### Issue: Quiz scores not updating proficiency
**Solution**: Check StudentProgress exists for the unit

### Issue: Ollama not found
**Solution**: Ensure Ollama is running and models are pulled

See [QUICKSTART.md](QUICKSTART.md) for more troubleshooting.

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG = False` in settings
- [ ] Configure PostgreSQL database
- [ ] Set secure `SECRET_KEY`
- [ ] Configure allowed hosts
- [ ] Set up HTTPS
- [ ] Collect static files
- [ ] Configure Ollama service
- [ ] Setup backups
- [ ] Monitor logs

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Khan Academy for the inspiration
- Django community for the excellent framework
- Ollama for the LLM integration

## 📧 Support

For issues, questions, or suggestions:
1. Check the documentation files
2. Review the troubleshooting guide
3. Open an issue on GitHub
4. Contact the development team

## 📊 Project Status

**Version**: 1.0  
**Status**: Production Ready ✅  
**Last Updated**: January 19, 2026

---

**Made with ❤️ for adaptive learning**
