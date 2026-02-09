import os
import django
from django.conf import settings
from django.template.loader import render_to_string

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

try:
    print("Attempting to render core/home.html...")
    content = render_to_string('core/home.html')
    print("Render successful!")
except Exception as e:
    print("Render failed!")
    print(e)
    import traceback
    traceback.print_exc()
