"""
db/vector_store.py

Handles embeddings and semantic search using ChromaDB (a lightweight,
local vector database — no cloud account needed, unlike MongoDB Atlas).

WHAT THIS ENABLES:
- Semantic search: "find tasks similar to this failure" using MEANING,
  not exact keyword matching.
- Failure analysis: the agent can search past failures by describing
  the problem in plain English, even if the wording is totally different.
- Explainability: when the agent makes a decision, it can look up
  similar past situations to justify *why* it's choosing an action.

HOW IT WORKS:
1. Every time something happens (a task runs, a conversation happens),
   we convert the relevant text into a vector ("embedding") using a
   free, local model (sentence-transformers — no API cost).
2. We store that vector + the original text in ChromaDB.
3. Later, when searching, we embed the SEARCH QUERY the same way, and
   ChromaDB finds the stored vectors that are mathematically closest
   to it — i.e. the most similar in MEANING.
"""

import chromadb
from sentence_transformers import SentenceTransformer

# This model converts text into vectors. It downloads once (~80MB) and
# then runs entirely locally — no API key, no per-call cost.
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# ChromaDB running in "persistent" mode — it saves to disk in this folder,
# so your embedded data survives between server restarts.
chroma_client = chromadb.PersistentClient(path="./chroma_data")

# One "collection" (like a table) for everything we embed.
# In a bigger system you might split this into multiple collections,
# but one is simpler and totally fine for this project's scope.
collection = chroma_client.get_or_create_collection(name="astranova_memory")


def embed_text(text: str) -> list:
    """Converts a string into its vector representation."""
    return embedding_model.encode(text).tolist()


def store_memory(text: str, metadata: dict, memory_id: str):
    """
    Embeds a piece of text and stores it in the vector database.

    text:      the actual content to embed, e.g. "Backup task failed:
               permission denied writing to D:\\backups"
    metadata:  extra structured info kept alongside the vector,
               e.g. {"task_type": "backup", "status": "failure"}
    memory_id: a unique ID for this entry (e.g. the MongoDB document ID,
               so we can trace a vector match back to its full record)
    """
    embedding = embed_text(text)
    collection.add(
        ids=[memory_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[metadata]
    )


def search_memory(query: str, n_results: int = 5, filter_metadata: dict = None) -> list:
    """
    Searches the vector store for entries semantically similar to `query`.

    query:           natural language search text, e.g. "why did backups fail"
    n_results:       how many matches to return
    filter_metadata: optional exact-match filter, e.g. {"task_type": "backup"}

    Returns a list of dicts with the matched text, metadata, and how
    close the match was (lower distance = more similar).
    """
    query_embedding = embed_text(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=filter_metadata
    )

    matches = []
    if results["documents"] and results["documents"][0]:
        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            matches.append({
                "text": doc,
                "metadata": meta,
                "similarity_distance": round(distance, 4)
            })
    return matches
