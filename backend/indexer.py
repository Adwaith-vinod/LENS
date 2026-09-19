from scanner import scan_directory
from text_extractor import extract_text
from chunker import chunk_text
from sentence_transformers import SentenceTransformer


model = SentenceTransformer("all-MiniLM-L6-v2")


def index_directory(folder_path):

    files = scan_directory(folder_path)

    all_chunks = []
    all_embeddings = []
    all_metadata = []

    chunk_id = 0

    for file in files:

        print(f"Processing: {file.name}")

        text = extract_text(file)

        if not text:
            print("  No text found. Skipping.")
            continue

        chunks = chunk_text(text, 500)

        embeddings = model.encode(chunks)

        for chunk, embedding in zip(chunks, embeddings):

            metadata = {
                "chunk_id": chunk_id,
                "file_name": file.name,
                "file_path": str(file)
            }

            all_chunks.append(chunk)
            all_embeddings.append(embedding)
            all_metadata.append(metadata)

            chunk_id += 1

        print(f"  Chunks: {len(chunks)}")

    return all_chunks, all_embeddings, all_metadata


if __name__ == "__main__":

    folder = "C:/Users/adwai/OneDrive/Documents"

    chunks, embeddings, metadata = index_directory(folder)

    print("\nIndexing complete!")
    print("Total chunks:", len(chunks))
    print("Total embeddings:", len(embeddings))
    print("Total metadata:", len(metadata))

    print("\nExample metadata:")
    print(metadata[0])