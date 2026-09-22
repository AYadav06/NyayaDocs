from typing import Optional
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.query_engine import BaseQueryEngine
from llama_index.core.response import Response
from llama_index.llms.google_genai import GoogleGenAI

from src.config import GEMINI_API_KEY, LLM_MODEL


def get_llm(
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: float = 0.2,
) -> GoogleGenAI:
    """Returns a configured GoogleGenAI LLM instance."""
    key = api_key or GEMINI_API_KEY
    if not key:
        raise ValueError("GEMINI_API_KEY is not set in environment or .env file.")

    return GoogleGenAI(
        model=model_name or LLM_MODEL,
        api_key=key,
        temperature=temperature,
    )


def create_query_engine(
    index: VectorStoreIndex,
    similarity_top_k: int = 4,
    response_mode: str = "compact",
) -> BaseQueryEngine:
    """
    Creates and returns a QueryEngine backed by Gemini LLM.
    """
    llm = get_llm()
    Settings.llm = llm

    return index.as_query_engine(
        similarity_top_k=similarity_top_k,
        response_mode=response_mode,
    )
