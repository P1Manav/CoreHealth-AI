# RAG retriever — top-k retrieval from the Chroma knowledge base.
# pyrefly: ignore [missing-import]
import chromadb
from sentence_transformers import SentenceTransformer
from app.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, EMBEDDING_MODEL_NAME, RAG_TOP_K

_embedding_model = None
_chroma_collection = None


# Lazy-load the embedding model.
def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


# Lazy-connect to Chroma collection.
def _get_collection():
    global _chroma_collection
    if _chroma_collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _chroma_collection = client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _chroma_collection


# Public accessor for the shared embedding model.
def get_embedding_model():
    return _get_embedding_model()


# Embed a single text string, returns list of floats.
def embed_text(text):
    return _get_embedding_model().encode(text).tolist()


# Embed a list of text strings, returns list of float-lists.
def embed_texts(texts):
    return _get_embedding_model().encode(texts).tolist()


# Retrieve top-k most relevant KB chunks for a query.
def retrieve(query, top_k=None):
    if top_k is None:
        top_k = RAG_TOP_K
    collection = _get_collection()
    if collection.count() == 0:
        return []
    query_embedding = embed_text(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "id": results["ids"][0][i],
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return chunks
