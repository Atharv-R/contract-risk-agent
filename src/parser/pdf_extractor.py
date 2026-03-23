"""
PDF Extractor — Pulls raw text from PDF contracts.

Uses pdfplumber as the primary engine (best for text-based PDFs),
falls back to PyMuPDF if pdfplumber struggles.
"""

from dataclasses import dataclass, field
from pathlib import Path
import pdfplumber
import fitz  # PyMuPDF


# ── Data Structures ──────────────────────────────────────────────
# These are just containers to keep our extracted data organized.

@dataclass
class PageContent:
    """Text content from a single page."""
    page_number: int
    text: str


@dataclass
class ExtractedDocument:
    """Complete extracted document with metadata."""
    filename: str
    total_pages: int
    pages: list[PageContent]
    full_text: str  # All pages joined together
    metadata: dict = field(default_factory=dict)


# ── Extraction Functions ─────────────────────────────────────────

def extract_with_pdfplumber(pdf_path: str) -> list[PageContent]:
    """
    Primary extraction method.
    pdfplumber is great at preserving layout and handling tables.
    """
    pages = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()

            # Sometimes a page has no extractable text (scanned image)
            if text and text.strip():
                pages.append(PageContent(
                    page_number=i + 1,
                    text=text.strip()
                ))

    return pages


def extract_with_pymupdf(pdf_path: str) -> list[PageContent]:
    """
    Fallback extraction method.
    PyMuPDF (fitz) handles some PDFs that pdfplumber can't.
    """
    pages = []
    doc = fitz.open(pdf_path)

    for i, page in enumerate(doc):
        text = page.get_text()

        if text and text.strip():
            pages.append(PageContent(
                page_number=i + 1,
                text=text.strip()
            ))

    doc.close()
    return pages


def get_pdf_metadata(pdf_path: str) -> dict:
    """Extract metadata like author, creation date, etc."""
    doc = fitz.open(pdf_path)
    meta = doc.metadata or {}
    doc.close()

    return {
        "author": meta.get("author", "Unknown"),
        "title": meta.get("title", ""),
        "creation_date": meta.get("creationDate", ""),
        "page_count": fitz.open(pdf_path).page_count,
    }


# ── Main Function (this is what the rest of the app calls) ───────

def extract_pdf(pdf_path: str) -> ExtractedDocument:
    """
    Extract text from a PDF contract.

    Tries pdfplumber first. If it gets less than 100 characters
    (probably a scanned PDF), falls back to PyMuPDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        ExtractedDocument with full text, per-page text, and metadata.

    Raises:
        FileNotFoundError: If the PDF doesn't exist.
        ValueError: If no text could be extracted.
    """
    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF file: {pdf_path}")

    # Try pdfplumber first
    pages = extract_with_pdfplumber(pdf_path)
    method_used = "pdfplumber"

    # If we got very little text, try PyMuPDF as fallback
    total_chars = sum(len(p.text) for p in pages)
    if total_chars < 100:
        pages = extract_with_pymupdf(pdf_path)
        method_used = "pymupdf"

    # If still nothing, the PDF is probably scanned images
    total_chars = sum(len(p.text) for p in pages)
    if total_chars < 100:
        raise ValueError(
            f"Could not extract meaningful text from {pdf_path}. "
            f"The PDF might be scanned images. OCR support coming soon."
        )

    # Combine all pages into one string
    full_text = "\n\n".join(page.text for page in pages)

    # Get metadata
    metadata = get_pdf_metadata(pdf_path)
    metadata["extraction_method"] = method_used
    metadata["total_characters"] = total_chars

    return ExtractedDocument(
        filename=path.name,
        total_pages=len(pages),
        pages=pages,
        full_text=full_text,
        metadata=metadata,
    )


# ── This lets you test the file directly ─────────────────────────
# Run: python -m src.parser.pdf_extractor

if __name__ == "__main__":
    import sys
    from rich import print as rprint

    if len(sys.argv) < 2:
        rprint("[yellow]Usage: python -m src.parser.pdf_extractor <path_to_pdf>[/yellow]")
        sys.exit(1)

    doc = extract_pdf(sys.argv[1])
    rprint(f"[green]✓ Extracted {doc.total_pages} pages from {doc.filename}[/green]")
    rprint(f"[green]✓ Total characters: {doc.metadata['total_characters']}[/green]")
    rprint(f"[green]✓ Method: {doc.metadata['extraction_method']}[/green]")
    rprint(f"\n[bold]First 500 characters:[/bold]\n")
    rprint(doc.full_text[:500])