"""
Clause Chunker — Splits contract text into meaningful clause-level chunks.

Legal documents have structure: numbered sections, titled articles, etc.
This module detects that structure and splits on clause boundaries
instead of arbitrary character counts.

Why this matters:
  Bad chunking:  "...shall not exceed $50,000. | 7. INTELLECTUAL PROPERTY..."
                  (splits mid-thought, mixes two topics)

  Good chunking: One chunk = one complete clause about one topic.
"""

import re
from dataclasses import dataclass, field


@dataclass
class ClauseChunk:
    """A single clause extracted from the contract."""
    text: str
    section_id: str = ""
    section_title: str = ""
    start_page: int = 0
    chunk_index: int = 0
    char_count: int = 0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        self.char_count = len(self.text)


# ── Section Header Patterns ──────────────────────────────────────
# Ordered from most specific to least specific.
# Only match TOP-LEVEL section headers (not subsections like 2.1, 2.2).

HEADER_PATTERNS = [
    # "Article I" "Article 5" "ARTICLE III"
    (
        r'(?:^|\n)((?:ARTICLE|Article)\s+\w+)[.\:\s—–-]+\s*([^\n]{2,80})',
        "article"
    ),
    # "Section 1" "SECTION 2"  (top-level only, no dots)
    (
        r'(?:^|\n)((?:SECTION|Section)\s+\d+)[.\:\s—–-]+\s*([^\n]{2,80})',
        "section"
    ),
    # "1." "2." "15." — top-level numbered sections
    # Must be followed by a title in CAPS or Title Case (not a subsection body)
    (
        r'(?:^|\n)(\d{1,2})\.\s+([A-Z][A-Z\s]{2,60}?)(?:\n|$)',
        "numbered_top"
    ),
]


def _find_section_breaks(text: str) -> list[dict]:
    """
    Scan the text for TOP-LEVEL section headers and return their positions.
    """
    breaks = []
    seen_positions = set()

    for pattern, pattern_type in HEADER_PATTERNS:
        for match in re.finditer(pattern, text):
            pos = match.start()

            # Skip if too close to an existing match
            if any(abs(pos - s) < 10 for s in seen_positions):
                continue

            section_id = match.group(1).strip()

            if match.lastindex >= 2:
                title = match.group(2).strip()
                title = re.sub(r'[.\:\s]+$', '', title)
            else:
                title = section_id.title()

            breaks.append({
                "start": pos,
                "section_id": section_id,
                "title": title,
                "type": pattern_type,
            })
            seen_positions.add(pos)

    breaks.sort(key=lambda x: x["start"])
    return breaks


def _split_on_breaks(text: str, breaks: list[dict]) -> list[ClauseChunk]:
    """Given the text and detected section breaks, extract each clause."""
    chunks = []

    for i, brk in enumerate(breaks):
        start = brk["start"]
        end = breaks[i + 1]["start"] if i + 1 < len(breaks) else len(text)
        chunk_text = text[start:end].strip()

        if len(chunk_text) < 30:
            continue

        chunks.append(ClauseChunk(
            text=chunk_text,
            section_id=brk["section_id"],
            section_title=brk["title"],
            chunk_index=i,
            metadata={"pattern_type": brk["type"]},
        ))

    return chunks


def _merge_small_chunks(chunks: list[ClauseChunk], min_size: int = 200) -> list[ClauseChunk]:
    """Merge very small chunks into their neighbors."""
    if len(chunks) <= 1:
        return chunks

    merged = []
    buffer = None

    for chunk in chunks:
        if buffer is None:
            buffer = chunk
            continue

        if buffer.char_count < min_size:
            # Merge small buffer into current chunk
            merged_text = buffer.text + "\n\n" + chunk.text
            buffer = ClauseChunk(
                text=merged_text,
                section_id=buffer.section_id,
                section_title=buffer.section_title or chunk.section_title,
                chunk_index=buffer.chunk_index,
            )
        else:
            merged.append(buffer)
            buffer = chunk

    if buffer:
        merged.append(buffer)

    return merged


def _fallback_chunking(text: str, max_chunk_size: int = 1500, overlap: int = 200) -> list[ClauseChunk]:
    """Fallback: split by paragraphs with a size limit."""
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    current_chunk = ""
    chunk_idx = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
            chunks.append(ClauseChunk(
                text=current_chunk.strip(),
                section_id=f"chunk_{chunk_idx + 1}",
                section_title="",
                chunk_index=chunk_idx,
                metadata={"pattern_type": "fallback_paragraph"},
            ))
            current_chunk = current_chunk[-overlap:] + "\n\n" + para
            chunk_idx += 1
        else:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append(ClauseChunk(
            text=current_chunk.strip(),
            section_id=f"chunk_{chunk_idx + 1}",
            section_title="",
            chunk_index=chunk_idx,
            metadata={"pattern_type": "fallback_paragraph"},
        ))

    return chunks


# ── Main Function ────────────────────────────────────────────────

def chunk_contract(text: str, min_sections: int = 3, max_chunk_size: int = 3000) -> list[ClauseChunk]:
    """
    Split contract text into clause-level chunks.

    Detects top-level section structure (numbered sections, articles).
    Falls back to paragraph-based splitting if structure isn't found.
    """
    if not text or len(text.strip()) < 50:
        return []

    # Step 1: Try to detect section structure
    breaks = _find_section_breaks(text)
    chunks = _split_on_breaks(text, breaks) if breaks else []

    # Step 2: Fallback if not enough sections found
    if len(chunks) < min_sections:
        chunks = _fallback_chunking(text, max_chunk_size=max_chunk_size)

    # Step 3: Merge very small chunks
    chunks = _merge_small_chunks(chunks, min_size=200)

    # Step 4: Split oversized chunks
    final_chunks = []
    for chunk in chunks:
        if chunk.char_count > max_chunk_size * 2:
            sub_chunks = _fallback_chunking(chunk.text, max_chunk_size=max_chunk_size)
            for j, sc in enumerate(sub_chunks):
                sc.section_id = f"{chunk.section_id}.part{j+1}"
                sc.section_title = chunk.section_title
                final_chunks.append(sc)
        else:
            final_chunks.append(chunk)

    # Re-index
    for i, chunk in enumerate(final_chunks):
        chunk.chunk_index = i

    return final_chunks


# ── Direct testing ───────────────────────────────────────────────

if __name__ == "__main__":
    from rich import print as rprint
    from rich.table import Table
    import sys

    # Test with PDF if provided, otherwise use sample text
    if len(sys.argv) > 1:
        from src.parser.pdf_extractor import extract_pdf
        doc = extract_pdf(sys.argv[1])
        text = doc.full_text
        rprint(f"[bold]Chunking PDF: {sys.argv[1]}[/bold]\n")
    else:
        text = """
1. DEFINITIONS

"Agreement" means this Master Services Agreement. "Company" refers to Acme Corp.

2. TERM AND RENEWAL

This Agreement shall automatically renew for successive one (1) year periods.

3. INTELLECTUAL PROPERTY

All work product shall be considered work for hire and assigned to Company.

4. LIABILITY

Company's liability shall not be limited in any way.

5. NON-COMPETE

Service Provider agrees not to compete for five (5) years.

6. GOVERNING LAW

This Agreement shall be governed by the laws of Delaware.
"""
        rprint("[bold]Chunking sample text[/bold]\n")

    chunks = chunk_contract(text)

    table = Table(title="Detected Clauses")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Section", style="green", width=12)
    table.add_column("Title", style="yellow", width=30)
    table.add_column("Chars", style="magenta", width=8)
    table.add_column("Preview", width=50)

    for c in chunks:
        preview = c.text[:80].replace("\n", " ") + "..."
        table.add_row(
            str(c.chunk_index),
            c.section_id,
            c.section_title[:28] if c.section_title else "(untitled)",
            str(c.char_count),
            preview,
        )

    rprint(table)
    rprint(f"\n[green]✓ Total chunks: {len(chunks)}[/green]")