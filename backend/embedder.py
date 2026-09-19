from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

text = "Python is used for machine learning"

embedding = model.encode(text)

print(embedding)
print("Number of values:", len(embedding))