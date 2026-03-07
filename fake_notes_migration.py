import os
import sys
import django
from django.core.management import call_command

# Add current directory to path
sys.path.append(os.getcwd())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "learnbridge.settings")
django.setup()

print("Attempting to fake migration 0002 for notes...")
try:
    call_command('migrate', 'notes', '0002', fake=True)
    print("Migration faked successfully.")
except Exception as e:
    print(f"Migration fake failed: {e}")
