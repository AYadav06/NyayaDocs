import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from src.config import (
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    LLM_MODEL,
    QDRANT_STORAGE_PATH,
)
from src.Ingestion.chunker import LlamaIndexChunker
from src.Ingestion.docling_parser import Parser
from src.Ingestion.vectordb import build_or_load_index, get_qdrant_client
from src.Query.query_engine import create_query_engine
from src.Retrieval.retriever import retrieve_relevant_nodes

# Global state for index & client
rag_state = {
    "index": None,
    "client": None,
}


def initialize_rag(max_initial_docs: Optional[int] = 2, force_rebuild: bool = False):
    """Initializes or loads the VectorStoreIndex."""
    client = get_qdrant_client()
    rag_state["client"] = client

    has_vectors = False
    try:
        collections = [c.name for c in client.get_collections().collections]
        if COLLECTION_NAME in collections:
            count = client.count(collection_name=COLLECTION_NAME).count
            has_vectors = count > 0 and not force_rebuild
            if has_vectors:
                print(f"📦 Found existing collection '{COLLECTION_NAME}' with {count} vectors.")
    except Exception as e:
        print(f"Notice during collection check: {e}")
        has_vectors = False

    if has_vectors:
        print("⚡ Loading VectorStoreIndex from existing Qdrant storage...")
        index = build_or_load_index(client=client, force_rebuild=force_rebuild)
    else:
        print("📚 No existing index found. Starting PDF ingestion with Docling...")
        pdf_dir = Path("data/20_pdf")
        if not pdf_dir.exists():
            print(f"⚠️ PDF directory '{pdf_dir}' not found.")
            return None

        parser = Parser()
        documents = parser.parse_directory(pdf_dir, max_docs=max_initial_docs)
        if not documents:
            print("⚠️ No documents parsed.")
            return None

        chunker = LlamaIndexChunker(chunk_size=1024, chunk_overlap=128)
        nodes = chunker.chunk_documents(documents)
        index = build_or_load_index(client=client, nodes=nodes, force_rebuild=force_rebuild)

    rag_state["index"] = index
    return index


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    print("🚀 Starting NyayaDocs API...")
    initialize_rag(max_initial_docs=2)
    yield
    print("🛑 Shutting down NyayaDocs API...")


# --- FastAPI App Definition ---
app = FastAPI(
    title="NyayaDocs RAG API",
    description="Legal document search and Q&A system using Docling, LlamaIndex, Qdrant, and Google Gemini.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend applications (Streamlit, React, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request & Response Models ---
class QueryRequest(BaseModel):
    query: str = Field(..., description="User query or legal question", example="What is this case about?")
    similarity_top_k: int = Field(default=4, ge=1, le=10, description="Number of top chunks to retrieve")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0, description="LLM sampling temperature")


class SourceNodeInfo(BaseModel):
    file_name: str
    score: Optional[float] = None
    snippet: str
    content: Optional[str] = None
    num_pages: Optional[int] = None


class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[SourceNodeInfo]


class RetrieveRequest(BaseModel):
    query: str = Field(..., description="Search query for vector similarity", example="Article 21 fundamental rights")
    similarity_top_k: int = Field(default=5, ge=1, le=10)


class RetrieveResponse(BaseModel):
    query: str
    count: int
    nodes: List[SourceNodeInfo]


class IngestRequest(BaseModel):
    pdf_dir: str = Field(default="data/20_pdf", description="Directory containing PDF files")
    max_docs: Optional[int] = Field(default=None, description="Max documents to parse (None for all)")
    force_rebuild: bool = Field(default=False, description="Whether to rebuild collection from scratch")


class IngestResponse(BaseModel):
    status: str
    documents_indexed: int
    total_vectors: int


class HealthResponse(BaseModel):
    status: str
    collection_name: str
    vector_count: int
    llm_model: str
    embedding_model: str


# --- Endpoints ---
@app.get("/", tags=["General"])
def root():
    return {
        "message": "Welcome to NyayaDocs RAG API",
        "docs": "/docs",
        "health": "/health",
        "llm_model": LLM_MODEL,
        "embedding_model": EMBEDDING_MODEL,
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
def health():
    client = rag_state.get("client") or get_qdrant_client()
    vector_count = 0
    try:
        vector_count = client.count(collection_name=COLLECTION_NAME).count
    except Exception:
        vector_count = 0

    return HealthResponse(
        status="ready" if rag_state.get("index") is not None else "no_index",
        collection_name=COLLECTION_NAME,
        vector_count=vector_count,
        llm_model=LLM_MODEL,
        embedding_model=EMBEDDING_MODEL,
    )


@app.post("/query", response_model=QueryResponse, tags=["RAG"])
def query_rag(request: QueryRequest):
    index = rag_state.get("index")
    if not index:
        index = initialize_rag()
        if not index:
            raise HTTPException(status_code=503, detail="Vector index is not initialized. Please run /ingest first.")

    try:
        query_engine = create_query_engine(
            index,
            similarity_top_k=request.similarity_top_k,
            temperature=request.temperature,
        )
        response = query_engine.query(request.query)

        sources = []
        for node_with_score in response.source_nodes:
            node = node_with_score.node
            full_content = node.get_content()
            snippet = full_content[:300].replace("\n", " ").strip()
            sources.append(
                SourceNodeInfo(
                    file_name=node.metadata.get("file_name", "Unknown"),
                    score=round(node_with_score.score, 4) if node_with_score.score else None,
                    snippet=snippet,
                    content=full_content,
                    num_pages=node.metadata.get("num_pages"),
                )
            )

        return QueryResponse(
            query=request.query,
            answer=str(response.response),
            sources=sources,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")


@app.post("/retrieve", response_model=RetrieveResponse, tags=["RAG"])
def retrieve_nodes(request: RetrieveRequest):
    index = rag_state.get("index")
    if not index:
        index = initialize_rag()
        if not index:
            raise HTTPException(status_code=503, detail="Vector index is not initialized.")

    try:
        nodes_with_score = retrieve_relevant_nodes(
            index,
            request.query,
            similarity_top_k=request.similarity_top_k,
        )

        sources = []
        for node_with_score in nodes_with_score:
            node = node_with_score.node
            full_content = node.get_content()
            snippet = full_content[:300].replace("\n", " ").strip()
            sources.append(
                SourceNodeInfo(
                    file_name=node.metadata.get("file_name", "Unknown"),
                    score=round(node_with_score.score, 4) if node_with_score.score else None,
                    snippet=snippet,
                    content=full_content,
                    num_pages=node.metadata.get("num_pages"),
                )
            )

        return RetrieveResponse(
            query=request.query,
            count=len(sources),
            nodes=sources,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval error: {str(e)}")


@app.post("/ingest", response_model=IngestResponse, tags=["Ingestion"])
def ingest_documents(request: IngestRequest):
    pdf_dir = Path(request.pdf_dir)
    if not pdf_dir.exists():
        raise HTTPException(status_code=404, detail=f"PDF directory '{pdf_dir}' not found.")

    try:
        parser = Parser()
        documents = parser.parse_directory(pdf_dir, max_docs=request.max_docs)
        if not documents:
            raise HTTPException(status_code=400, detail="No PDF files could be parsed.")

        chunker = LlamaIndexChunker(chunk_size=1024, chunk_overlap=128)
        nodes = chunker.chunk_documents(documents)

        client = rag_state.get("client") or get_qdrant_client()
        index = build_or_load_index(
            client=client,
            nodes=nodes,
            force_rebuild=request.force_rebuild,
        )
        rag_state["index"] = index

        total_vectors = client.count(collection_name=COLLECTION_NAME).count

        return IngestResponse(
            status="success",
            documents_indexed=len(documents),
            total_vectors=total_vectors,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
