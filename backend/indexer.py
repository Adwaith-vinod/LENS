from scanner import scan_directory
from text_extractor import extract_text
from chunker import chunk_text
from sentence_transformers import SentenceTransformer


model = SentenceTransformer("all-MiniLM-L6-v2")


def index_directory(folder_path):

    files = scan_directory(folder_path)

    all_chunks = []
    all_embeddings = []

    for file in files:

        print(f"Processing: {file.name}")

        text = extract_text(file)

        if not text:
            print("  No text found. Skipping.")
            continue

        chunks = chunk_text(text, 500)

        embeddings = model.encode(chunks)

        all_chunks.extend(chunks)
        all_embeddings.extend(embeddings)

        print(f"  Chunks: {len(chunks)}")

    return all_chunks, all_embeddings


if __name__ == "__main__":

    folder = "C:/Users/adwai/OneDrive/Documents"

    chunks, embeddings = index_directory(folder)

    print("\nIndexing complete!")
    print("Total chunks:", len(chunks))
    print("Total embeddings:", len(embeddings))