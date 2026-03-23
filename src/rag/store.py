"""
Vector Store — Ingests the clause library into ChromaDB.

ChromaDB stores our embeddings locally (no server needed).
We chunk each markdown file by section headers, embed each chunk,
and store it with metadata so we can retrieve relevant baselines later.

Run this file directly to ingest:  python -m src.rag.store
"""

import re
from pathlib import Path
from dataclasses import dataclass

import chromadb

from src.rag.embedder import embed_texts


# ── Config ───────────────────────────────────────────────────────

CLAUSE_LIBRARY_PATH = Path("clause_library")
VECTORSTORE_PATH = Path("data/vectorstore")
COLLECTION_NAME = "clause_library"


# ── Data Structures ──────────────────────────────────────────────

@dataclass
class LibraryChunk:
    """A chunk from a clause library markdown file."""
    text: str               # The actual content
    clause_type: str        # "auto_renewal", "liability_cap", etc.
    section: str            # "Red Flags", "Standard and Acceptable", etc.
    source_file: str        # "auto_renewal.md"
    chunk_id: str           # Unique ID for ChromaDB


# ── Markdown Chunking ────────────────────────────────────────────

def _parse_markdown_file(filepath: Path) -> list[LibraryChunk]:
    """
    Split a clause library markdown file into chunks by ## headers.

    Each section (## What It Is, ## Red Flags, etc.) becomes its own
    chunk so retrieval can be precise.
    """
    text = filepath.read_text(encoding="utf-8")
    clause_type = filepath.stem  # "auto_renewal" from "auto_renewal.md"

    # Split on ## headers
    sections = re.split(r'\n## ', text)
    chunks = []

    for i, section in enumerate(sections):
        section = section.strip()
        if not section or len(section) < 20:
            continue

        # First section starts with # Title
        if section.startswith("# "):
            lines = section.split("\n", 1)
            section_name = "Overview"
            content = lines[1].strip() if len(lines) > 1 else ""
        else:
            # Subsequent sections start with the header text (## was split off)
            lines = section.split("\n", 1)
            section_name = lines[0].strip()
            content = lines[1].strip() if len(lines) > 1 else ""

        if not content or len(content) < 20:
            continue

        # Prepend context so the embedding knows what this chunk is about
        contextualized = (
            f"Clause type: {clause_type.replace('_', ' ').title()}\n"
            f"Section: {section_name}\n\n"
            f"{content}"
        )

        chunk_id = f"{clause_type}__{section_name.lower().replace(' ', '_')}__{i}"

        chunks.append(LibraryChunk(
            text=contextualized,
            clause_type=clause_type,
            section=section_name,
            source_file=filepath.name,
            chunk_id=chunk_id,
        ))

    return chunks


def load_all_library_chunks() -> list[LibraryChunk]:
    """Load and chunk all markdown files from the clause library."""
    all_chunks = []

    if not CLAUSE_LIBRARY_PATH.exists():
        raise FileNotFoundError(f"Clause library not found: {CLAUSE_LIBRARY_PATH}")

    md_files = sorted(CLAUSE_LIBRARY_PATH.glob("*.md"))

    if not md_files:
        raise FileNotFoundError(f"No .md files found in {CLAUSE_LIBRARY_PATH}")

    for filepath in md_files:
        chunks = _parse_markdown_file(filepath)
        all_chunks.extend(chunks)
        print(f"  Parsed {filepath.name}: {len(chunks)} chunks")

    return all_chunks


# ── ChromaDB Operations ──────────────────────────────────────────

def get_chroma_client() -> chromadb.PersistentClient:
    """Get a persistent ChromaDB client."""
    VECTORSTORE_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(VECTORSTORE_PATH))


def get_or_create_collection(client: chromadb.PersistentClient) -> chromadb.Collection:
    """Get the clause library collection, creating it if needed."""
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Contract clause baseline library"},
    )


def ingest_clause_library(force_rebuild: bool = False):
    """
    Load all clause library markdown files, embed them, and store in ChromaDB.

    Args:
        force_rebuild: If True, delete existing collection and rebuild from scratch.
    """
    print("\n📚 Ingesting clause library into vector store...\n")

    client = get_chroma_client()

    # Optionally wipe and rebuild
    if force_rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
            print("  Deleted existing collection (force rebuild)")
        except Exception:
            pass

    collection = get_or_create_collection(client)

    # Check if already ingested
    existing_count = collection.count()
    if existing_count > 0 and not force_rebuild:
        print(f"  Collection already has {existing_count} chunks. Skipping ingestion.")
        print(f"  (Use force_rebuild=True to re-ingest)\n")
        return existing_count

    # Load and chunk all markdown files
    chunks = load_all_library_chunks()
    print(f"\n  Total chunks to embed: {len(chunks)}")

    # Embed all chunks in one batch
    texts = [chunk.text for chunk in chunks]
    print(f"  Embedding {len(texts)} chunks...")
    embeddings = embed_texts(texts)

    # Store in ChromaDB
    collection.add(
        ids=[chunk.chunk_id for chunk in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {
                "clause_type": chunk.clause_type,
                "section": chunk.section,
                "source_file": chunk.source_file,
            }
            for chunk in chunks
        ],
    )

    final_count = collection.count()
    print(f"\n✅ Ingestion complete! {final_count} chunks stored in ChromaDB.")
    print(f"   Stored at: {VECTORSTORE_PATH}\n")

    return final_count


# ── Direct Execution ─────────────────────────────────────────────

if __name__ == "__main__":
    ingest_clause_library(force_rebuild=True)