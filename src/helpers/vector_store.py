import chromadb
from sympy import python
from helpers import config

Settings = config.get_settings()

client = chromadb.HttpClient(
    host=Settings.CHROMA_HOST,
    port=Settings.CHROMA_PORT
)

collection = client.get_or_create_collection(
    name="document_chunks"
)

def store_chunks(
    chunks: list[str],
    embeddings,
    subject_id: int,
    document_id: int,
):
    collection.upsert(
        ids=[
            f"subject_{subject_id}_doc_{document_id}_chunk_{i}"
            for i in range(len(chunks))
        ],
        documents=chunks,
        embeddings=embeddings.tolist(),
        metadatas=[
            {
                "subject_id": subject_id,
                "document_id": document_id,
                "chunk_index": i,
            }
            for i in range(len(chunks))
        ],
    )
    
def search_chunks(
    query_embedding,
    subject_id: int,
    document_id: int,
    top_k: int = 3,
):
    return collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=top_k,
        where={
            "$and": [
                {"subject_id": {"$eq": subject_id}},
                {"document_id": {"$eq": document_id}},
            ]
        },
        include=["documents", "metadatas", "distances"],
    )

def has_document_chunks(subject_id: int, document_id: int) -> bool:
    results = collection.get(
        where={
            "$and": [
                {"subject_id": {"$eq": subject_id}},
                {"document_id": {"$eq": document_id}},
            ]
        },
        limit=1,
        include=["metadatas"],
    )
    return bool(results["ids"])