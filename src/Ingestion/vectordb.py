import atexit
from pathlib import Path
import sys
import time
from typing import Dict, List, Optional, Set
import qdrant_client
from llama_index.core import (
    Document,
    Settings,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.schema import BaseNode
from llama_index.vector_stores.qdrant import QdrantVectorStore

from src.config import (
    COLLECTION_NAME,
    QDRANT_STORAGE_PATH,
    QDRANT_URL,
    QDRANT_API_KEY,
)
from src.Ingestion.chunker import LlamaIndexChunker
from src.Ingestion.embedding import get_embedding_model

# Cache clients per path/URL to prevent file lock collisions or redundant network sessions
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
    url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> qdrant_client.QdrantClient:
    """Initializes and returns a Qdrant client, reusing instances for local or cloud storage."""
    target_url = url or QDRANT_URL
    target_api_key = api_key or QDRANT_API_KEY

    # 1. Connect to Qdrant Cloud if URL is provided
    if target_url:
        cache_key = f"cloud_{target_url}"
        if cache_key not in _CLIENT_CACHE:
            print(f"Connecting to Qdrant Cloud at {target_url}...")
            _CLIENT_CACHE[cache_key] = qdrant_client.QdrantClient(
                url=target_url,
                api_key=target_api_key,
            )
        return _CLIENT_CACHE[cache_key]

    # 2. In-memory mode for temporary tests
    if in_memory:
        return qdrant_client.QdrantClient(":memory:")

    # 3. Local disk storage fallback
    resolved_path = str(Path(storage_path or QDRANT_STORAGE_PATH).resolve())
    Path(resolved_path).mkdir(parents=True, exist_ok=True)

    if resolved_path not in _CLIENT_CACHE:
        _CLIENT_CACHE[resolved_path] = qdrant_client.QdrantClient(path=resolved_path)

    return _CLIENT_CACHE[resolved_path]


def get_indexed_file_names(
    client: qdrant_client.QdrantClient,
    collection_name: str = COLLECTION_NAME,
) -> Set[str]:
    """Returns a set of file names that have already been indexed in the Qdrant collection."""
    try:
        collections = [c.name for c in client.get_collections().collections]
        if collection_name not in collections:
            return set()

        file_names: Set[str] = set()
        offset = None
        while True:
            records, next_offset = client.scroll(
                collection_name=collection_name,
                limit=250,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for r in records:
                if r.payload:
                    fn = r.payload.get("file_name") or r.payload.get("metadata", {}).get("file_name")
                    if fn:
                        file_names.add(fn)
            if not next_offset:
                break
            offset = next_offset
        return file_names
    except Exception as e:
        print(f"Notice while checking existing indexed files: {e}")
        return set()


def insert_nodes_with_retry(
    index: VectorStoreIndex,
    nodes: List[BaseNode],
    max_retries: int = 5,
    initial_delay: float = 15.0,
):
    """Inserts nodes into an existing VectorStoreIndex with exponential backoff on 429 rate limit errors."""
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            index.insert_nodes(nodes)
            return
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                if attempt == max_retries:
                    raise
                print(f"Gemini Rate limit (429) hit. Pausing {int(delay)}s before retry (Attempt {attempt}/{max_retries})...")
                time.sleep(delay)
                delay *= 1.5
            else:
                raise


def build_or_load_index(
    nodes: Optional[List[BaseNode]] = None,
    documents: Optional[List[Document]] = None,
    client: Optional[qdrant_client.QdrantClient] = None,
    storage_path: Optional[str] = None,
    collection_name: str = COLLECTION_NAME,
    force_rebuild: bool = False,
) -> Optional[VectorStoreIndex]:
    """
    Builds a new VectorStoreIndex into Qdrant or loads an existing one.
    Ensures Gemini embedding model is registered in LlamaIndex Settings.
    """
    # 1. Ensure Gemini embeddings are set globally in LlamaIndex
    embed_model = get_embedding_model()
    Settings.embed_model = embed_model

    # 2. Connect Qdrant client
    qdrant_cli = client or get_qdrant_client(storage_path=storage_path)

    # 3. Handle force_rebuild by deleting existing collection
    if force_rebuild:
        try:
            collections = [c.name for c in qdrant_cli.get_collections().collections]
            if collection_name in collections:
                print(f"Force rebuild: Deleting existing collection '{collection_name}'...")
                qdrant_cli.delete_collection(collection_name=collection_name)
        except Exception as e:
            print(f"Notice while deleting collection for force rebuild: {e}")

    vector_store = QdrantVectorStore(client=qdrant_cli, collection_name=collection_name)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # 4. Check if collection already exists and has vectors
    collection_exists = False
    try:
        collections = [c.name for c in qdrant_cli.get_collections().collections]
        if collection_name in collections:
            count = qdrant_cli.count(collection_name=collection_name).count
            collection_exists = count > 0
            if collection_exists:
                print(f"Found existing Qdrant collection '{collection_name}' with {count} vectors.")
    except Exception:
        collection_exists = False

    # If no new nodes or documents are passed, this is a pure load operation
    if nodes is None and documents is None:
        if collection_exists:
            print("Loading VectorStoreIndex from existing Qdrant storage...")
            return VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                storage_context=storage_context,
            )
        else:
            return None

    # 5. If documents are provided but not nodes, chunk them first
    if nodes is None and documents is not None:
        chunker = LlamaIndexChunker()
        nodes = chunker.chunk_documents(documents)

    if not nodes:
        raise ValueError("No nodes or documents provided to build the vector index!")

    # 6. Index nodes into Qdrant
    if collection_exists and not force_rebuild:
        print(f"Inserting {len(nodes)} new chunks into existing Qdrant collection '{collection_name}'...")
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
        )
        insert_nodes_with_retry(index, nodes)
        print("Chunks inserted into Qdrant successfully.")
    else:
        print(f"Indexing {len(nodes)} chunks into Qdrant collection '{collection_name}'...")
        index = VectorStoreIndex(
            nodes=nodes,
            storage_context=storage_context,
        )
        print("Index built and saved to Qdrant successfully.")

    return index


def ingest_directory_incrementally(
    pdf_dir: str = "data/20_pdf",
    force_rebuild: bool = False,
    sleep_between_docs: float = 1.5,
) -> Optional[VectorStoreIndex]:
    """
    Parses, chunks, and indexes PDFs one document at a time.
    Resilient to rate limits and saves progress continuously.
    """
    from src.Ingestion.docling_parser import Parser

    path = Path(pdf_dir)
    if not path.exists():
        print(f"Directory '{pdf_dir}' not found.")
        return None

    pdf_files = sorted(list(path.glob("*.pdf")))
    if not pdf_files:
        print(f"No PDF files found in '{pdf_dir}'.")
        return None

    client = get_qdrant_client()

    if force_rebuild:
        print(f"Force rebuild requested. Clearing collection '{COLLECTION_NAME}'...")
        try:
            client.delete_collection(collection_name=COLLECTION_NAME)
        except Exception:
            pass

    indexed_files = get_indexed_file_names(client, COLLECTION_NAME)
    remaining_files = [f for f in pdf_files if f.name not in indexed_files]

    print("\n" + "=" * 60)
    print(f"Total PDFs found in '{pdf_dir}': {len(pdf_files)}")
    print(f"Already indexed in Qdrant ('{COLLECTION_NAME}'): {len(indexed_files)}")
    print(f"Remaining to index: {len(remaining_files)}")
    print("=" * 60 + "\n")

    if not remaining_files:
        print("All documents are already indexed in Qdrant.")
        return build_or_load_index(client=client)

    # Load or initialize the vector index
    index = build_or_load_index(client=client)
    parser = Parser()
    chunker = LlamaIndexChunker(chunk_size=512, chunk_overlap=64)

    for i, pdf_path in enumerate(remaining_files, 1):
        print(f"\n[{i}/{len(remaining_files)}] Parsing '{pdf_path.name}' with Docling...")
        try:
            doc = parser.parse_file(pdf_path)
            if not doc:
                print(f"Notice: Failed to extract text from {pdf_path.name}. Skipping.")
                continue

            nodes = chunker.chunk_documents([doc])
            if not nodes:
                print(f"Notice: No text chunks generated for {pdf_path.name}. Skipping.")
                continue

            print(f"   -> Generated {len(nodes)} chunks. Embedding & inserting into Qdrant...")

            if index is None:
                index = build_or_load_index(client=client, nodes=nodes)
            else:
                insert_nodes_with_retry(index, nodes)

            total_vectors = client.count(collection_name=COLLECTION_NAME).count
            print(f"   Saved '{pdf_path.name}' to Qdrant (Collection now has {total_vectors} vectors).")

            if sleep_between_docs > 0 and i < len(remaining_files):
                time.sleep(sleep_between_docs)

        except Exception as e:
            print(f"Error processing {pdf_path.name}: {e}")
            continue

    final_count = client.count(collection_name=COLLECTION_NAME).count
    print(f"\nIngestion complete. Total vectors in collection '{COLLECTION_NAME}': {final_count}")
    return index


if __name__ == "__main__":
    force = "--force-rebuild" in sys.argv
    ingest_directory_incrementally("data/20_pdf", force_rebuild=force)
