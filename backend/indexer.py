from pathlib import Path

from text_extractor import extract_text
from chunker import chunk_text
from sentence_transformers import SentenceTransformer


model = SentenceTransformer("all-MiniLM-L6-v2")


def index_file(file_path):

    # 1. Extract text
    text = extract_text(file_path)

    if not text:
        print("No text found.")
        return

    # 2. Split text into chunks
    chunks = chunk_text(text, 500)

    # 3. Convert chunks into embeddings
    embeddings = model.encode(chunks)

    print("File:", file_path)
    print("Number of chunks:", len(chunks))
    print("Embedding shape:", embeddings.shape)

    return chunks, embeddings


file = "C:/Users/adwai/OneDrive/Documents/INTERNREPORT[1]_final_final.pdf"

chunks, embeddings = index_file(file)