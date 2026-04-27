import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer

print("LOADING DATA...")

df = pd.read_csv("final_trendingtopics_reddit.csv")

texts = df["text_translated"].fillna("").astype(str).tolist()

print("TOTAL POSTS:", len(texts))

print("LOADING EMBEDDING MODEL...")
model = SentenceTransformer("all-MiniLM-L6-v2")

print("CREATING EMBEDDINGS...")
embeddings = model.encode(texts, show_progress_bar=True)

print("SAVING EMBEDDINGS...")
np.save("sentence_embeddings.npy", embeddings)

print("DONE")
print("Embeddings shape:", embeddings.shape)