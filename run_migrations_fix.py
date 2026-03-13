import os
import sys
import django
from django.core.management import call_command
from django.db import connection

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "learnbridge.settings")
django.setup()

try:
    print("Checking database connection...")
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    print("Database connection OK.")
    
    print("Running migrate...")
    call_command('migrate', 'course', verbosity=3)
    print("Migrate finished.")
    
    print("Verifying table existence...")
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='course_conceptmap'")
        result = cursor.fetchone()
        if result:
            print(f"Table {result[0]} EXISTS!")
        else:
            print("Table DOES NOT exist.")
except Exception as e:
    print(f"Error: {e}")
finally:
    connection.close()
