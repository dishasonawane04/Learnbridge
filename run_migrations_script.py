import os
import sys
import django
from django.core.management import call_command

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "learnbridge.settings")
django.setup()

try:
    print("Running makemigrations...")
    call_command('makemigrations', 'course', verbosity=3)
    print("makemigrations finished.")
    
    print("Running migrate...")
    call_command('migrate', 'course', verbosity=3)
    print("migrate finished.")
except Exception as e:
    print(f"Error: {e}")
