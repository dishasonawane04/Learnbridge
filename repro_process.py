import sys
import os

# Setup Django
sys.path.append('d:\\DISHA\\learnbridge')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
import django
django.setup()

from ai_engine.course_processor import process_document

def test_process():
    print("Testing process_document with dummy.txt...")
    file_path = os.path.join(os.getcwd(), 'dummy.txt')
    try:
        # Use a dummy course_id like 999
        success = process_document(file_path, 999)
        if success:
            print("Processing SUCCESS")
        else:
            print("Processing FAILED (returned False)")
    except Exception as e:
        print(f"Processing CRASHED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_process()
