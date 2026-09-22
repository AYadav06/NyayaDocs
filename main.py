import sys
from pathlib import Path
from src.config import COLLECTION_NAME, QDRANT_STORAGE_PATH
from src.Ingestion.chunker import LlamaIndexChunker
from src.Ingestion.docling_parser import Parser
from src.Ingestion.vectordb import build_or_load_index, get_qdrant_client



def main():
    print("Initializing PageTrail RAG System...")

    # 1. Check if Qdrant vector store already has indexed documents
    client = get_qdrant_client()
    has_vectors = False
    try:
        collections = [c.name for c in client.get_collections().collections]
        if COLLECTION_NAME in collections:
            count = client.count(collection_name=COLLECTION_NAME).count
            has_vectors = count > 0
            if has_vectors:
                print(f"⚡Found existing collection '{COLLECTION_NAME}' with {count} vectors.")
    except Exception as e:
        print(f"Notice: Could not inspect collection: {e}")
        has_vectors = False

    # 2. Build or load the vector index
    if has_vectors:
        print("Loading index from Qdrant storage...")
        index = build_or_load_index(client=client)
    else:
        print("No existing index found. Starting PDF ingestion with Docling...")
        pdf_dir = Path("data/20_pdf")
        if not pdf_dir.exists():
            print(f"Error: Directory '{pdf_dir}' does not exist!")
            return

        # For fast startup, parse 2 PDFs first (remove max_docs=2 to parse all PDFs)
        parser = Parser()
        documents = parser.parse_directory(pdf_dir, max_docs=2)

        if not documents:
            print("No documents parsed. Exiting.")
            return

        print("Chunking documents into nodes...")
        chunker = LlamaIndexChunker(chunk_size=1024, chunk_overlap=128)
        nodes = chunker.chunk_documents(documents)

        print("Embedding chunks and saving to Qdrant...")
        index = build_or_load_index(client=client, nodes=nodes)

if __name__ == "__main__":
    main()
