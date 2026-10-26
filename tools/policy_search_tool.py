import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Optional, Type

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr


POLICY_COLLECTION_NAME = "company_policies"
POLICY_STORE_PATH = Path(__file__).resolve().parents[1] / "chroma_data"
PolicySearchEventCallback = Callable[[str, dict[str, Any]], None]


class PolicySearchInput(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="Customer question to search in the company policy records.",
    )
    result_count: int = Field(default=5, ge=1, le=10)


@lru_cache(maxsize=1)
def _get_policy_collection():
    client = chromadb.PersistentClient(path=str(POLICY_STORE_PATH))
    embedding_function = SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return client.get_collection(
        name=POLICY_COLLECTION_NAME,
        embedding_function=embedding_function,
    )


class PolicySearchTool(BaseTool):
    name: str = "search_company_policies"
    description: str = (
        "Search the ingested company policy collection in Chroma for relevant "
        "policy records. Use retrieved policies as the sole source for policy "
        "answers, and mention when the evidence is insufficient."
    )
    args_schema: Type[BaseModel] = PolicySearchInput
    _event_callback: Optional[PolicySearchEventCallback] = PrivateAttr(
        default=None
    )

    def __init__(
        self,
        event_callback: Optional[PolicySearchEventCallback] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._event_callback = event_callback

    def _notify(self, event: str, payload: dict[str, Any]) -> None:
        if self._event_callback:
            self._event_callback(event, payload)

    def _run(self, query: str, result_count: int = 5) -> str:
        self._notify(
            "policy_search_started",
            {"message": "Customer Care is searching the company policy collection."},
        )
        try:
            collection = _get_policy_collection()
            total = collection.count()
            if total == 0:
                raise ValueError("The company policy collection is empty.")

            matches = collection.query(
                query_texts=[query],
                n_results=min(result_count, total),
                include=["documents", "metadatas", "distances"],
            )
            documents = matches["documents"]
            metadatas = matches["metadatas"]
            distances = matches["distances"]
            if documents is None or metadatas is None or distances is None:
                raise RuntimeError("Chroma returned incomplete policy results.")

            results = [
                {
                    "policy_id": metadata.get("policy_id", "Unknown policy"),
                    "title": metadata.get("section", "Company policy"),
                    "similarity": max(0.0, min(1.0, 1.0 - float(distance))),
                    "content": document,
                }
                for document, metadata, distance in zip(
                    documents[0], metadatas[0], distances[0]
                )
            ]
            self._notify(
                "policy_search_completed",
                {
                    "message": f"Retrieved {len(results)} relevant policy record(s).",
                    "policies": [
                        {
                            "policy_id": result["policy_id"],
                            "title": result["title"],
                            "similarity": result["similarity"],
                        }
                        for result in results
                    ],
                },
            )
            return json.dumps(results, ensure_ascii=False)
        except Exception as error:
            self._notify(
                "policy_search_error",
                {"message": f"Policy search failed: {error}"},
            )
            raise
