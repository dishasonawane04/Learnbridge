import sys
import os
print(f"Python Executable: {sys.executable}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")
print(f"sys.path: {sys.path}")

try:
    import langchain_community
    print("langchain_community: SUCCESS")
except ImportError as e:
    print(f"langchain_community: FAILED ({e})")

try:
    from langchain_community.vectorstores import FAISS
    print("FAISS: SUCCESS")
except ImportError as e:
    print(f"FAISS: FAILED ({e})")

try:
    import sentence_transformers
    print("sentence_transformers: SUCCESS")
except ImportError as e:
    print(f"sentence_transformers: FAILED ({e})")

try:
    import torch
    print("torch: SUCCESS")
except ImportError as e:
    print(f"torch: FAILED ({e})")
