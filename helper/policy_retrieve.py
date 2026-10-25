
import chromadb
from chromadb.utils.embedding_functions import (
    SentenceTransformerEmbeddingFunction
)

embedding_fn = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

client = chromadb.PersistentClient(path="./chroma_data")

collection = client.get_collection(
    name="company_policies",
    embedding_function=embedding_fn
)

query = "Can I return my laptop after 12 days?"

results = collection.query(
    query_texts=[query],
    n_results=3,
    include=["documents", "metadatas", "distances"]
)

for doc, meta, distance in zip(
    results["documents"][0],
    results["metadatas"][0],
    results["distances"][0]
):
    print("Policy:", meta.get("policy_id"))
    print("Category:", meta.get("category"))
    print("Distance:", round(distance, 4))
    print("Content:", doc)
    print("-" * 50)
