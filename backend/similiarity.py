from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer("all-MiniLM-L6-v2")

text1 = "Python is used for machine learning"
text2 = "The weather is very hot today"

embedding1 = model.encode([text1])
embedding2 = model.encode([text2])

score = cosine_similarity(embedding1, embedding2)

print("Similarity:", score[0][0])