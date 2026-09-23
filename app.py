import html
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import requests
import streamlit as st

st.set_page_config(
    page_title="NyayaDocs",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Main background & headers */
    .main-header {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(12px);
    }

    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #38BDF8 0%, #818CF8 50%, #C084FC 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        padding-bottom: 6px;
    }

    .subtitle {
        color: #94A3B8;
        font-size: 1.05rem;
        margin: 0;
    }

    /* Source Citation Card (Expandable on click) */
    details.citation-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(56, 189, 248, 0.2);
        border-radius: 10px;
        padding: 14px 16px;
        margin-top: 10px;
        margin-bottom: 8px;
        transition: all 0.2s ease-in-out;
        cursor: pointer;
    }

    details.citation-card:hover {
        border-color: rgba(56, 189, 248, 0.5);
        background: rgba(30, 41, 59, 0.75);
        box-shadow: 0 4px 14px rgba(56, 189, 248, 0.08);
    }

    details.citation-card[open] {
        border-color: rgba(56, 189, 248, 0.6);
        background: rgba(15, 23, 42, 0.85);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
    }

    details.citation-card summary {
        list-style: none;
        outline: none;
        cursor: pointer;
        user-select: none;
    }

    details.citation-card summary::-webkit-details-marker {
        display: none;
    }

    .citation-badge {
        display: inline-block;
        background: rgba(56, 189, 248, 0.15);
        color: #38BDF8;
        font-weight: 600;
        font-size: 0.8rem;
        padding: 3px 8px;
        border-radius: 6px;
        margin-right: 6px;
    }

    .score-badge {
        display: inline-block;
        background: rgba(99, 102, 241, 0.15);
        color: #A5B4FC;
        font-size: 0.8rem;
        padding: 3px 8px;
        border-radius: 6px;
        margin-right: 6px;
    }

    .pages-badge {
        display: inline-block;
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        font-size: 0.8rem;
        padding: 3px 8px;
        border-radius: 6px;
    }

    .expand-hint {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 0.78rem;
        font-weight: 500;
        color: #38BDF8;
        background: rgba(56, 189, 248, 0.1);
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid rgba(56, 189, 248, 0.25);
        transition: all 0.2s ease;
    }

    details.citation-card:hover .expand-hint {
        background: rgba(56, 189, 248, 0.2);
        border-color: rgba(56, 189, 248, 0.5);
    }

    .collapse-hint {
        display: none;
        align-items: center;
        gap: 4px;
        font-size: 0.78rem;
        font-weight: 500;
        color: #94A3B8;
        background: rgba(148, 163, 184, 0.1);
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid rgba(148, 163, 184, 0.2);
    }

    details.citation-card[open] .expand-hint {
        display: none;
    }

    details.citation-card[open] .collapse-hint {
        display: inline-flex;
    }

    .citation-full-container {
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid rgba(56, 189, 248, 0.15);
        cursor: auto;
    }

    .full-content-body {
        background: rgba(10, 15, 29, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 14px 16px;
        color: #F1F5F9;
        font-size: 0.92rem;
        line-height: 1.65;
        white-space: pre-wrap;
        word-break: break-word;
        max-height: 420px;
        overflow-y: auto;
        user-select: text;
    }

    .full-content-body::-webkit-scrollbar {
        width: 6px;
    }
    .full-content-body::-webkit-scrollbar-thumb {
        background: rgba(56, 189, 248, 0.3);
        border-radius: 3px;
    }

    .prompt-btn {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 8px 12px;
        cursor: pointer;
        color: #E2E8F0;
        font-size: 0.9rem;
    }

    /* Stat Box */
    .stat-box {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 14px;
        text-align: center;
        margin-bottom: 12px;
    }
    .stat-number {
        font-size: 1.6rem;
        font-weight: 700;
        color: #38BDF8;
    }
    .stat-label {
        font-size: 0.8rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Backend Helper Functions ---
DEFAULT_API_URL = "http://localhost:8000"


def check_backend_health(api_url: str) -> Optional[Dict[str, Any]]:
    """Checks connection to the FastAPI backend."""
    try:
        resp = requests.get(f"{api_url}/health", timeout=2)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def query_fastapi(api_url: str, query: str, top_k: int, temperature: float) -> Dict[str, Any]:
    """Sends a query to the FastAPI /query endpoint."""
    resp = requests.post(
        f"{api_url}/query",
        json={"query": query, "similarity_top_k": top_k, "temperature": temperature},
        timeout=60,
    )
    if resp.status_code == 200:
        return resp.json()
    else:
        raise RuntimeError(f"API Error ({resp.status_code}): {resp.text}")


def trigger_fastapi_ingest(api_url: str, max_docs: Optional[int], force_rebuild: bool) -> Dict[str, Any]:
    """Triggers document ingestion via FastAPI /ingest endpoint."""
    resp = requests.post(
        f"{api_url}/ingest",
        json={"max_docs": max_docs, "force_rebuild": force_rebuild},
        timeout=300,
    )
    if resp.status_code == 200:
        return resp.json()
    else:
        raise RuntimeError(f"Ingestion Error ({resp.status_code}): {resp.text}")


# --- Direct In-Process Fallback Engine (when FastAPI is not running) ---
@st.cache_resource(show_spinner="Initializing RAG pipeline locally...")
def get_local_rag_index():
    """Initializes local VectorStoreIndex fallback if FastAPI is offline."""
    from src.Ingestion.vectordb import build_or_load_index, get_qdrant_client
    from src.Ingestion.docling_parser import Parser
    from src.Ingestion.chunker import LlamaIndexChunker
    from src.config import COLLECTION_NAME

    client = get_qdrant_client()
    has_vectors = False
    try:
        collections = [c.name for c in client.get_collections().collections]
        if COLLECTION_NAME in collections:
            has_vectors = client.count(COLLECTION_NAME).count > 0
    except Exception:
        has_vectors = False

    if has_vectors:
        return build_or_load_index(client=client)

    pdf_dir = Path("data/20_pdf")
    if pdf_dir.exists():
        parser = Parser()
        docs = parser.parse_directory(pdf_dir, max_docs=2)
        if docs:
            chunker = LlamaIndexChunker()
            nodes = chunker.chunk_documents(docs)
            return build_or_load_index(client=client, nodes=nodes)
    return None


def query_local_pipeline(query: str, top_k: int, temperature: float) -> Dict[str, Any]:
    """Queries local LlamaIndex engine directly."""
    from src.Query.query_engine import create_query_engine

    index = get_local_rag_index()
    if not index:
        raise RuntimeError("No local vector index found. Please index documents first.")

    query_engine = create_query_engine(index, similarity_top_k=top_k, temperature=temperature)
    response = query_engine.query(query)

    sources = []
    for node_with_score in response.source_nodes:
        node = node_with_score.node
        full_content = node.get_content()
        sources.append(
            {
                "file_name": node.metadata.get("file_name", "Unknown"),
                "score": round(node_with_score.score, 4) if node_with_score.score else None,
                "snippet": full_content[:300].replace("\n", " ").strip(),
                "content": full_content,
                "num_pages": node.metadata.get("num_pages"),
            }
        )

    return {
        "query": query,
        "answer": str(response.response),
        "sources": sources,
    }


def render_citation_card(idx: int, s: Dict[str, Any]) -> str:
    """Renders an interactive expandable citation card showing snippet and full content on click."""
    file_name = html.escape(str(s.get("file_name", "Unknown Document")))
    score = s.get("score")
    score_text = f"Confidence: {int(score * 100)}%" if score else "Retrieved"
    snippet = html.escape(str(s.get("snippet", "")).strip())
    content = s.get("content") or s.get("snippet") or "No content available."
    escaped_content = html.escape(str(content).strip())
    num_pages = s.get("num_pages")
    page_badge = f'<span class="pages-badge">📄 {num_pages} pages</span>' if num_pages else ""
    char_count = f"{len(content):,} chars"

    return f"""
    <details class="citation-card">
        <summary>
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 6px;">
                    <span class="citation-badge">[{idx}] {file_name}</span>
                    <span class="score-badge">{score_text}</span>
                    {page_badge}
                </div>
                <div>
                    <span class="expand-hint">🔍 Click to view full content ▾</span>
                    <span class="collapse-hint">🔼 Click to collapse</span>
                </div>
            </div>
            <p style="color: #CBD5E1; font-size: 0.92rem; margin-top: 10px; margin-bottom: 2px; line-height: 1.5;">
                "{snippet}..."
            </p>
        </summary>
        <div class="citation-full-container">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="color: #38BDF8; font-weight: 600; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px;">
                    📖 Complete Retrieved Content Chunk
                </span>
                <span style="color: #94A3B8; font-size: 0.78rem;">
                    {char_count}
                </span>
            </div>
            <div class="full-content-body">{escaped_content}</div>
        </div>
    </details>
    """


# --- Initialize Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Namaste! I am **NyayaDocs**, your AI Legal Research Assistant for Supreme Court of India judgments.\n\nAsk me any question about the indexed judgments, case numbers, statutory interpretations, or legal principles.",
            "sources": [],
        }
    ]

# --- Sidebar UI ---
with st.sidebar:
    st.markdown("### System Configuration")

    api_url = st.text_input("FastAPI Backend URL", value=DEFAULT_API_URL)

    # Test backend connection
    backend_status = check_backend_health(api_url)

    if backend_status:
        st.success("FastAPI Server Connected")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f"""
                <div class="stat-box">
                    <div class="stat-number">{backend_status.get('vector_count', 0)}</div>
                    <div class="stat-label">Vectors</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f"""
                <div class="stat-box">
                    <div class="stat-number">{backend_status.get('collection_name', 'pagetrail')}</div>
                    <div class="stat-label">Collection</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        use_fastapi = True
    else:
        st.warning("FastAPI Offline — Using In-Process Direct Engine", icon="⚡")
        st.caption("To start FastAPI: `uv run uvicorn main:app --reload`")
        use_fastapi = False

    st.markdown("---")
    st.markdown("###  Retrieval Settings")
    top_k = st.slider("Top Chunks (similarity_top_k)", min_value=1, max_value=8, value=4)
    temperature = st.slider("Temperature (Creativity)", min_value=0.0, max_value=1.0, value=0.2, step=0.05)

    st.markdown("---")
    st.markdown("###  Document Ingestion")
    max_docs_input = st.number_input("Max PDFs to Ingest", min_value=1, max_value=50, value=2)
    force_rebuild = st.checkbox("Force Rebuild Collection", value=False)

    if st.button("Ingest / Re-index PDFs", use_container_width=True):
        with st.spinner("Parsing PDFs with Docling & Embedding with Gemini..."):
            try:
                if use_fastapi:
                    res = trigger_fastapi_ingest(api_url, int(max_docs_input), force_rebuild)
                    st.success(f"Indexed {res.get('documents_indexed')} docs ({res.get('total_vectors')} vectors)!")
                else:
                    from src.Ingestion.docling_parser import Parser
                    from src.Ingestion.chunker import LlamaIndexChunker
                    from src.Ingestion.vectordb import build_or_load_index, get_qdrant_client

                    p = Parser()
                    docs = p.parse_directory("data/20_pdf", max_docs=int(max_docs_input))
                    chunker = LlamaIndexChunker()
                    nodes = chunker.chunk_documents(docs)
                    client = get_qdrant_client()
                    build_or_load_index(client=client, nodes=nodes, force_rebuild=force_rebuild)
                    st.success(f"Indexed {len(docs)} documents ({len(nodes)} chunks) into Qdrant!")
                st.rerun()
            except Exception as e:
                st.error(f"Ingestion failed: {e}")

    st.markdown("---")
    if st.button("Clear Chat History", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Conversation cleared. How can I assist you with your legal research today?",
                "sources": [],
            }
        ]
        st.rerun()


# Header Hero Banner
st.markdown(
    """
    <div class="main-header">
        <h1 class="main-title">⚖️ NyayaDocs Legal AI</h1>
        <p class="subtitle">High-fidelity Retrieval-Augmented Generation for Supreme Court of India judgments.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab1, tab2 = st.tabs([" Legal Assistant Chat", " Indexed PDF Documents"])


with tab1:
    # Sample Query Quick-Pills
    st.markdown("<p style='color: #94A3B8; font-size: 0.85rem; margin-bottom: 6px;'>Quick prompts to try:</p>", unsafe_allow_html=True)
    pill_col1, pill_col2, pill_col3 = st.columns(3)

    sample_query = None
    with pill_col1:
        if st.button("Civil Appeal No. 3639 of 2022", use_container_width=True):
            sample_query = "What was the decision and main issue in Civil Appeal No. 3639 of 2022?"
    with pill_col2:
        if st.button(" Fundamental Rights under Art. 21", use_container_width=True):
            sample_query = "What observations did the court make regarding fundamental rights?"
    with pill_col3:
        if st.button(" Summary of Appellant Arguments", use_container_width=True):
            sample_query = "Summarize the key legal arguments presented by the appellant."

    # Display Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="‍⚖️" if msg["role"] == "user" else "⚖️"):
            st.markdown(msg["content"])

            # Render Expandable Citations for Assistant Responses
            sources = msg.get("sources", [])
            if sources:
                with st.expander(f"📚 Retrieved Sources & Citations ({len(sources)} citations)"):
                    for idx, s in enumerate(sources, 1):
                        st.markdown(render_citation_card(idx, s), unsafe_allow_html=True)

    # Chat Input Box
    user_query = st.chat_input("Ask a question about the legal judgments...")
    prompt_to_send = sample_query or user_query

    if prompt_to_send:
        # 1. Add user message to state
        st.session_state.messages.append({"role": "user", "content": prompt_to_send, "sources": []})
        with st.chat_message("user", avatar="🧑‍⚖️"):
            st.markdown(prompt_to_send)

        # 2. Generate assistant response
        with st.chat_message("assistant", avatar="⚖️"):
            with st.spinner("Searching judgments & synthesizing answer with Gemini 2.5 Flash..."):
                try:
                    if use_fastapi:
                        res = query_fastapi(api_url, prompt_to_send, top_k, temperature)
                    else:
                        res = query_local_pipeline(prompt_to_send, top_k, temperature)

                    answer = res.get("answer", "No answer synthesized.")
                    sources = res.get("sources", [])

                    st.markdown(answer)

                    # Display citations
                    if sources:
                        with st.expander(f"📚 Retrieved Sources & Citations ({len(sources)} citations)", expanded=True):
                            for idx, s in enumerate(sources, 1):
                                st.markdown(render_citation_card(idx, s), unsafe_allow_html=True)

                    # Save assistant response to session
                    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})

                except Exception as e:
                    st.error(f"❌ Error generating answer: {str(e)}")


with tab2:
    st.markdown("### 📂 Supreme Court of India PDF Corpus")
    pdf_dir = Path("data/20_pdf")

    if pdf_dir.exists():
        pdf_files = sorted(list(pdf_dir.glob("*.pdf")))
        st.write(f"Total PDF files available in `data/20_pdf`: **{len(pdf_files)}**")

        doc_data = []
        for f in pdf_files:
            size_kb = round(f.stat().st_size / 1024, 1)
            doc_data.append({"File Name": f.name, "File Size (KB)": f"{size_kb} KB", "Path": str(f)})

        st.dataframe(doc_data, use_container_width=True)

        st.markdown("---")
        st.markdown("### 🔍 Document Inspector & Reader")
        selected_file_name = st.selectbox(
            "Select a judgment PDF to read or download:",
            options=[f.name for f in pdf_files],
            key="doc_browser_select",
        )
        if selected_file_name:
            selected_path = pdf_dir / selected_file_name
            col_info1, col_info2 = st.columns([3, 1])
            with col_info1:
                st.markdown(
                    f"**File:** `{selected_file_name}` &nbsp;|&nbsp; "
                    f"**Size:** `{round(selected_path.stat().st_size / 1024, 1)} KB`"
                )
            with col_info2:
                with open(selected_path, "rb") as f_pdf:
                    st.download_button(
                        label="📥 Download Original PDF",
                        data=f_pdf.read(),
                        file_name=selected_file_name,
                        mime="application/pdf",
                        use_container_width=True,
                    )

            if st.button(f"📖 Extract and View Text ({selected_file_name})", key=f"btn_read_{selected_file_name}"):
                with st.spinner(f"Extracting text from {selected_file_name}..."):
                    try:
                        from src.Ingestion.docling_parser import Parser

                        parser = Parser()
                        parsed_doc = parser.parse_file(selected_path)
                        st.markdown(
                            f"""
                            <div style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 8px; padding: 18px; margin-top: 12px; max-height: 600px; overflow-y: auto; color: #F1F5F9; font-size: 0.95rem; line-height: 1.7; white-space: pre-wrap;">
{html.escape(parsed_doc.text)}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    except Exception as e:
                        st.error(f"Error parsing document: {e}")
    else:
        st.warning("`data/20_pdf` directory not found.")
