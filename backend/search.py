from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer("all-MiniLM-L6-v2")

documents = [
    "Dijkstra's algorithm is used to find the shortest path between nodes in a graph.",
    "Normalization in DBMS reduces data redundancy and improves database consistency.",
    "Python is widely used for machine learning and artificial intelligence.",
    "TCP provides reliable and ordered delivery of data over a network."
]

query = "Which document talks about shortest path algorithms?"

document_embeddings = model.encode(documents)
query_embedding = model.encode([query])

similarities = cosine_similarity(
    query_embedding,
    document_embeddings
)[0]

for i, score in enumerate(similarities):
    print(documents[i])
    print("Similarity:", score)
    print()