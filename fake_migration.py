import os
import sys
import django
from django.core.management import call_command

# Add current directory to path
sys.path.append(os.getcwd())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "learnbridge.settings")
django.setup()

print("Attempting to fake migration 0015...")
try:
    call_command('migrate', 'course', '0015', fake=True)
    print("Migration faked successfully.")
except Exception as e:
    print(f"Migration fake failed: {e}")
