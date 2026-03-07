import os
import sys
import django

# Add current directory to path
sys.path.append(os.getcwd())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "learnbridge.settings")
django.setup()

from course.models import Course

print("Testing query with is_deleted...")
try:
    count = Course.objects.filter(is_deleted=False).count()
    print(f"Success! Found {count} non-deleted courses.")
except Exception as e:
    print(f"Query failed: {e}")
