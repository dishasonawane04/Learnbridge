try:
    import reportlab
    print("reportlab is installed")
except ImportError:
    print("reportlab is MISSING")

try:
    import docx
    print("python-docx is installed")
except ImportError:
    print("python-docx is MISSING")
