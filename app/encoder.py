from sentence_transformers import SentenceTransformer 

MODEL_NAME = 'multi-qa-MiniLM-L6-cos-v1'

model = SentenceTransformer(MODEL_NAME, device='cpu')

def encode_text(text: str) -> list[float]:
    return model.encode(text).tolist()