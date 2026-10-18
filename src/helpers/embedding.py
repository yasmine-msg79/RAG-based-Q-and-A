from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

documents = {}

model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(chunks):
    embeddings = model.encode(chunks)
    return embeddings

def semantic_search(query, chunks, embeddings, top_k=3):
    query_embedding = model.encode([query])

    similarities = cosine_similarity(
        query_embedding, embeddings
    )[0]

    top_indices = similarities.argsort()[::-1][:top_k]

    return [
        {
            "text": chunks[i],
            "score": float(similarities[i])
        }
        for i in top_indices
    ]