from typing import Optional
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from src.config import GEMINI_API_KEY, EMBEDDING_MODEL


def get_embedding_model(
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> GoogleGenAIEmbedding:
    """Returns a configured GoogleGenAIEmbedding instance."""
    key = api_key or GEMINI_API_KEY
    if not key:
        raise ValueError("GEMINI_API_KEY is not set in environment or .env file.")

    return GoogleGenAIEmbedding(
        model_name=model_name or EMBEDDING_MODEL,
        embed_batch_size=100,
        api_key=key,
    )


if __name__ == "__main__":
    embed_model = get_embedding_model()
