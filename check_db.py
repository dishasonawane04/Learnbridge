import os
import sys
import django
from django.db import connection

# Add current directory to path
sys.path.append(os.getcwd())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "learnbridge.settings")
django.setup()

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'course_%'")
        tables = cursor.fetchall()
        for table in tables:
            print(table[0])
except Exception as e:
    print(f"Error: {e}")
