import os
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


@lru_cache(maxsize=1)
def get_langfuse_client():
    required_keys = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    if missing_keys:
        raise ValueError(
            "Langfuse is not configured. Set "
            + ", ".join(missing_keys)
            + " in the project .env file."
        )

    from langfuse import get_client

    return get_client()


@lru_cache(maxsize=1)
def instrument_crewai() -> None:
    from openinference.instrumentation.crewai import CrewAIInstrumentor

    CrewAIInstrumentor().instrument(skip_dep_check=True)


def get_langfuse_dashboard_url() -> str:
    base_url = os.getenv("LANGFUSE_BASE_URL", "").strip()
    return (base_url or "https://cloud.langfuse.com").rstrip("/")


def initialize_langfuse():
    client = get_langfuse_client()
    instrument_crewai()
    return client
