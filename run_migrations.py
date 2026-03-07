import os
import sys
import django
from django.core.management import call_command

# Add current directory to path
sys.path.append(os.getcwd())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "learnbridge.settings")
django.setup()

print("Attempting makemigrations...")
try:
    call_command('makemigrations', 'course')
    print("makemigrations success.")
except Exception as e:
    print(f"makemigrations failed: {e}")

print("Attempting migrate...")
try:
    call_command('migrate', 'course')
    print("migrate success.")
except Exception as e:
    print(f"migrate failed: {e}")
