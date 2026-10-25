
import json
import chromadb
from chromadb.utils.embedding_functions import (
    SentenceTransformerEmbeddingFunction
)
from pathlib import Path

# 1. Load the JSON file


json_path = (
    Path(__file__).resolve().parents[1]
    / "data_assets"
    / "sample_company_policy_knowledge_base.json"
)

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Supports a top-level list or a dictionary containing policies
if isinstance(data, list):
    policies = data
else:
    policies = data.get("policies", data.get("records", []))

if not isinstance(policies, list):
    raise ValueError("Expected a list of policy records")

# 2. Initialize embedding model
embedding_fn = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# 3. Initialize persistent ChromaDB
DB_DIR = "./chroma_data"
client = chromadb.PersistentClient(path=DB_DIR)

collection = client.get_or_create_collection(
    name="company_policies",
    embedding_function=embedding_fn,
    metadata={"description": "Company policy knowledge base"}
)

# 4. Prepare documents
ids = []
documents = []
metadatas = []

for policy in policies:
    policy_id = str(policy["policy_id"])

    # Convert policy content to searchable text
    document = "\n".join([
        f"Title: {policy.get('title', '')}",
        f"Section: {policy.get('section', '')}",
        f"Subsection: {policy.get('subsection', '')}",
        f"Content: {policy.get('content', '')}",
        f"Conditions: {json.dumps(policy.get('conditions', []))}",
        f"Exceptions: {json.dumps(policy.get('exceptions', []))}",
        f"Rules: {json.dumps(policy.get('rules', []))}",
        f"Example questions: {json.dumps(policy.get('example_questions', []))}"
    ])

    # Keep filterable metadata as simple values
    metadata = {}

    for key in [
        "policy_id", "section", "subsection",
        "category", "customer_type",
        "product_category", "approval_role",
        "escalation_role", "version"
    ]:
        value = policy.get(key)
        if isinstance(value, (str, int, float, bool)):
            metadata[key] = value

    ids.append(policy_id)
    documents.append(document)
    metadatas.append(metadata)

# 5. Insert or update policy records
if ids:
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

print(f"Processed {len(ids)} policy records")
print(f"Total stored: {collection.count()}")
