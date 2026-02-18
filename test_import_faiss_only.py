try:
    from langchain_community.vectorstores import FAISS
    print("Import FAISS Success")
except ImportError as e:
    print(f"Import FAISS Failed: {e}")
except Exception as e:
    print(f"Import FAISS Error: {e}")
