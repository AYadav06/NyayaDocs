from pathlib import Path
from typing import List, Optional
from docling.document_converter import DocumentConverter
from llama_index.core import Document


class Parser:
    """Parses PDF documents using Docling into LlamaIndex Document Objects."""

    def __init__(self):
        self.converter = DocumentConverter()

    def parse_file(self, pdf_path: Path | str) -> Document:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"Pdf not found at {pdf_path}")

        result = self.converter.convert(pdf_path)
        markdown_text = result.document.export_to_markdown()

        doc = Document(
            text=markdown_text,
            metadata={
                "file_name": pdf_path.name,
                "file_path": str(pdf_path.resolve()),
                "num_pages": len(result.document.pages),
            },
        )
        return doc

    def parse_directory(
        self, dir_path: Path | str, max_docs: Optional[int] = None
    ) -> List[Document]:
        """Parses all PDFs in a directory."""
        dir_path = Path(dir_path)
        pdf_files = sorted(list(dir_path.glob("*.pdf")))
        if max_docs:
            pdf_files = pdf_files[:max_docs]

        print(f"Found {len(pdf_files)} PDF(s) in {dir_path}")
        documents = []
        for pdf_file in pdf_files:
            try:
                doc = self.parse_file(pdf_file)
                documents.append(doc)
            except Exception as e:
                print(f"Error parsing {pdf_file.name}: {e}")

        return documents


