import atexit
from pathlib import Path
from typing import Dict, List, Optional
import qdrant_client
from llama_index.core import (
    Document,
    Settings,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.schema import BaseNode
from llama_index.vector_stores.qdrant import QdrantVectorStore

from src.config import COLLECTION_NAME, QDRANT_STORAGE_PATH
from src.Ingestion.chunker import LlamaIndexChunker
from src.Ingestion.docling_parser import Parser
from src.Ingestion.embedding import get_embedding_model

# Cache clients per path to prevent file lock collisions in local Qdrant
_CLIENT_CACHE: Dict[str, qdrant_client.QdrantClient] = {}


def _cleanup_qdrant_clients():
    """Cleanly close all local Qdrant clients on program exit."""
    for client in list(_CLIENT_CACHE.values()):
        try:
            client.close()
        except Exception:
            pass
    _CLIENT_CACHE.clear()


atexit.register(_cleanup_qdrant_clients)


def get_qdrant_client(
    storage_path: Optional[str] = None,
    in_memory: bool = False,
) -> qdrant_client.QdrantClient:
    """Initializes and returns a Qdrant client, reusing instances for local storage."""
    if in_memory:
        return qdrant_client.QdrantClient(":memory:")

    resolved_path = str(Path(storage_path or QDRANT_STORAGE_PATH).resolve())
    Path(resolved_path).mkdir(parents=True, exist_ok=True)

    if resolved_path not in _CLIENT_CACHE:
        _CLIENT_CACHE[resolved_path] = qdrant_client.QdrantClient(path=resolved_path)

    return _CLIENT_CACHE[resolved_path]


def build_or_load_index(
    nodes: Optional[List[BaseNode]] = None,
    documents: Optional[List[Document]] = None,
    client: Optional[qdrant_client.QdrantClient] = None,
    storage_path: Optional[str] = None,
    collection_name: str = COLLECTION_NAME,
    force_rebuild: bool = False,
) -> VectorStoreIndex:
    """
    Builds a new VectorStoreIndex into Qdrant or loads an existing one.
    Ensures Gemini embedding model is registered in LlamaIndex Settings.
    """
    # 1. Ensure Gemini embeddings are set globally in LlamaIndex
    embed_model = get_embedding_model()
    Settings.embed_model = embed_model

    # 2. Connect Qdrant client & vector store
    qdrant_cli = client or get_qdrant_client(storage_path=storage_path)
    vector_store = QdrantVectorStore(client=qdrant_cli, collection_name=collection_name)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # 3. Check if collection already exists and has vectors
    collection_exists = False
    try:
        collections = [c.name for c in qdrant_cli.get_collections().collections]
        if collection_name in collections:
            count = qdrant_cli.count(collection_name=collection_name).count
            if count > 0 and not force_rebuild:
                collection_exists = True
                print(f"Found existing Qdrant collection '{collection_name}' with {count} vectors.")
    except Exception:
        collection_exists = False

    if collection_exists and not force_rebuild:
        print("Loading VectorStoreIndex from existing Qdrant storage...")
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
        )
        return index

    # 4. If nodes not provided but documents are, chunk them first
    if nodes is None and documents is not None:
        chunker = LlamaIndexChunker()
        nodes = chunker.chunk_documents(documents)

    if not nodes:
        raise ValueError("No nodes or documents provided to build the vector index!")

    print(f"Indexing {len(nodes)} chunks into Qdrant collection '{collection_name}'...")
    index = VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
    )
    print("Index built and saved to Qdrant successfully.")
    return index


if __name__ == "__main__":
    print("Testing Vector DB Indexing with 1 sample PDF...")
    parser = Parser()
    sample_docs = parser.parse_directory("data/20_pdf", max_docs=1)

    if sample_docs:
        chunker = LlamaIndexChunker(chunk_size=512, chunk_overlap=64)
        sample_nodes = chunker.chunk_documents(sample_docs)
        index = build_or_load_index(nodes=sample_nodes)
        print("Index test completed successfully!")
    else:
        print("No sample PDFs found in data/20_pdf.")
