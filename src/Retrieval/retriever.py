from typing import List, Optional
from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore


def get_retriever(
    index: VectorStoreIndex,
    similarity_top_k: int = 5,
) -> BaseRetriever:
    """Returns a retriever from the VectorStoreIndex."""
    return index.as_retriever(similarity_top_k=similarity_top_k)


def retrieve_relevant_nodes(
    index: VectorStoreIndex,
    query_str: str,
    similarity_top_k: int = 5,
) -> List[NodeWithScore]:
    """Retrieves top-k relevant nodes for a given query string."""
    retriever = get_retriever(index, similarity_top_k=similarity_top_k)
    return retriever.retrieve(query_str)
