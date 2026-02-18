import torch
from transformers import AutoTokenizer, AutoModel
import numpy as np

def test_custom_embedding():
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    print(f"Loading {model_name} via transformers...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)
        
        text = "This is a test sentence."
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        
        with torch.no_grad():
            outputs = model(**inputs)
            # Mean Pooling - Take attention mask into account for correct averaging
            token_embeddings = outputs.last_hidden_state
            attention_mask = inputs['attention_mask']
            
            input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
            embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
            
            # Normalize
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            
        print(f"Embedding successful. Shape: {embeddings.shape}")
        return True
    except Exception as e:
        print(f"Custom Embedding Failed: {e}")
        return False

if __name__ == "__main__":
    test_custom_embedding()
