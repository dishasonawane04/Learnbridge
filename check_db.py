import os
import sys
import django
from django.db import connection

# Add current directory to path
sys.path.append(os.getcwd())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "learnbridge.settings")
django.setup()

print("Schema for course_course:")
try:
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(course_course)")
        columns = cursor.fetchall()
        for col in columns:
            print(col)
except Exception as e:
    print(f"Error: {e}")
