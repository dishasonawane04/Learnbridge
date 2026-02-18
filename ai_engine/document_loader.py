from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
import os

def load_document(file_path):
    """
    Load generic document based on file extension.
    Supports PDF and DOCX.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        loader = PyPDFLoader(file_path)
    elif ext in ['.docx', '.doc']:
        loader = Docx2txtLoader(file_path)
    elif ext == '.txt':
        from langchain_community.document_loaders import TextLoader
        loader = TextLoader(file_path, encoding='utf-8')
    else:
        # Fallback or raise error? For now return empty list or handle text files
        return []
        
    pages = loader.load()
    return pages
