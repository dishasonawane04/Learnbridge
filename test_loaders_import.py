try:
    from langchain_community.document_loaders import PyPDFLoader
    print("PyPDFLoader: SUCCESS")
except ImportError as e:
    print(f"PyPDFLoader: FAILED ({e})")

try:
    from langchain_community.document_loaders import Docx2txtLoader
    print("Docx2txtLoader: SUCCESS")
except ImportError as e:
    print(f"Docx2txtLoader: FAILED ({e})")
