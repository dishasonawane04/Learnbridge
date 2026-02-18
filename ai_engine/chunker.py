from langchain_text_splitters import RecursiveCharacterTextSplitter

def split_into_chunks(pages):
    """
    Split documents into chunks for Local RAG (Ollama).
    Chunk Size: 800 (Better for smaller context windows)
    Overlap: 150
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        add_start_index=True
    )
    return splitter.split_documents(pages)
