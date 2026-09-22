from typing import List, Optional
from llama_index.core import Document
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.core.schema import BaseNode

# sentence-Splitter chunking

class LlamaIndexChunker:
    """Chunks LlamaIndex Documents into smaller Nodes (chunks) for retrieval."""

    def __init__(
        self,
        chunk_size: int = 1024,
        chunk_overlap: int = 128,
        use_markdown_parser: bool = True,
    ):
        """
        Args:
            chunk_size: Maximum token count per chunk.
            chunk_overlap: Overlapping tokens between consecutive chunks to prevent lost context.
            use_markdown_parser: If True, first breaks document down by Markdown headers.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_markdown_parser = use_markdown_parser


           # sentence spiltter
        self.sentence_splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

              # markdown parser
        self.md_parser = MarkdownNodeParser() if use_markdown_parser else None

    def chunk_documents(self, documents: List[Document]) -> List[BaseNode]:
        """Transforms full documents into a list of chunk nodes."""
        if not documents:
            return []

        if self.use_markdown_parser:
            md_nodes = self.md_parser.get_nodes_from_documents(documents)
            nodes = self.sentence_splitter.get_nodes_from_documents(md_nodes)
        else:
            nodes = self.sentence_splitter.get_nodes_from_documents(documents)

        print(f"Chunked {len(documents)} document(s) into {len(nodes)} node chunks.")
        return nodes
