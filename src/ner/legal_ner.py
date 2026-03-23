"""
Legal NER — Extracts structured entities from contract text.

Combines spaCy's built-in NER (good at names, orgs, dates, money)
with custom regex patterns for legal-specific entities that spaCy
misses (durations, legal terms, percentages).

Entity types we extract:
  PARTY        → Companies and people in the contract
  DATE         → Specific dates ("January 15, 2025")
  DURATION     → Time periods ("36 months", "five (5) years")
  MONEY        → Dollar amounts ("$50,000", "six figures")
  JURISDICTION → States, countries, governing law locations
  PERCENTAGE   → Rates ("1.5% per month")
  LEGAL_TERM   → Key legal concepts the agent should flag
"""

import re
from dataclasses import dataclass, field
from collections import defaultdict

import spacy


# ── Data Structures ──────────────────────────────────────────────

@dataclass
class Entity:
    """A single extracted entity."""
    text: str             # The actual text: "Acme Corp"
    label: str            # Entity type: "PARTY"
    start: int = 0        # Character position in source text
    end: int = 0
    source: str = ""      # "spacy" or "regex" — useful for debugging
    context: str = ""     # Surrounding text for disambiguation


@dataclass
class ContractEntities:
    """All entities extracted from a contract, organized by type."""
    parties: list[Entity] = field(default_factory=list)
    dates: list[Entity] = field(default_factory=list)
    durations: list[Entity] = field(default_factory=list)
    money: list[Entity] = field(default_factory=list)
    jurisdictions: list[Entity] = field(default_factory=list)
    percentages: list[Entity] = field(default_factory=list)
    legal_terms: list[Entity] = field(default_factory=list)

    @property
    def all_entities(self) -> list[Entity]:
        """Flat list of every entity."""
        return (
            self.parties + self.dates + self.durations +
            self.money + self.jurisdictions +
            self.percentages + self.legal_terms
        )

    @property
    def summary(self) -> dict:
        """Quick count summary for display."""
        return {
            "parties": len(self.parties),
            "dates": len(self.dates),
            "durations": len(self.durations),
            "money": len(self.money),
            "jurisdictions": len(self.jurisdictions),
            "percentages": len(self.percentages),
            "legal_terms": len(self.legal_terms),
            "total": len(self.all_entities),
        }

    def unique_values(self, label: str) -> list[str]:
        """Get deduplicated entity texts for a given label."""
        entities = getattr(self, label, [])
        seen = set()
        unique = []
        for e in entities:
            normalized = e.text.strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(e.text.strip())
        return unique


# ── spaCy Model Loading ──────────────────────────────────────────

# Load once, reuse everywhere (this is a ~12MB model)
_nlp = None

def _get_nlp():
    """Lazy-load the spaCy model so it only loads when first needed."""
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


# ── Regex Patterns for Legal-Specific Entities ───────────────────

# Duration patterns: "twelve (12) months", "5 years", "thirty-six (36) month"
DURATION_PATTERNS = [
    # "twelve (12) months" / "thirty-six (36) month period"
    r'(?:(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|'
    r'thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|'
    r'thirty|forty|fifty|sixty|ninety|hundred)'
    r'[-\s]*(?:(?:one|two|three|four|five|six|seven|eight|nine))?'
    r'\s*\(\d+\)\s*(?:month|year|day|week|business day)s?(?:\s*period)?)',

    # "(12) months" / "(36) month period"
    r'\(\d+\)\s*(?:month|year|day|week|business day)s?(?:\s*period)?',

    # "12 months" / "36 months" / "5 years"
    r'\b\d+\s*(?:month|year|day|week|business day)s?(?:\s*period)?\b',

    # "one year" / "two years" etc. without parenthetical
    r'\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|'
    r'twenty|thirty|sixty|ninety)\s+(?:month|year|day|week)s?\b',
]

# Percentage patterns: "1.5%", "1.5% per month"
PERCENTAGE_PATTERNS = [
    r'\b\d+(?:\.\d+)?%\s*(?:per\s+(?:month|year|annum|day))?\b',
]

# Money patterns spaCy might miss: "$50,000.00", "six figures"
MONEY_PATTERNS = [
    r'\$\s*[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|thousand|USD))?',
    r'\b\d+(?:,\d{3})+(?:\.\d{2})?\s*(?:dollars|USD)\b',
]

# Legal terms that are important for risk analysis
LEGAL_TERMS = [
    "auto-renewal", "automatic renewal", "automatically renew",
    "auto-renew", "evergreen",
    "uncapped liability", "unlimited liability", "no limitation",
    "no cap", "without limitation",
    "intellectual property", "work for hire", "work made for hire",
    "ip assignment", "assigns all right",
    "non-compete", "non-competition", "noncompete",
    "non-solicitation", "non-solicitation",
    "indemnify", "indemnification", "hold harmless",
    "defend and indemnify",
    "confidential information", "trade secret", "proprietary",
    "non-disclosure",
    "termination for convenience", "terminate at any time",
    "termination for cause",
    "force majeure", "act of god",
    "governing law", "jurisdiction", "arbitration",
    "binding arbitration", "mandatory arbitration",
    "waiver of jury trial", "jury trial",
    "consequential damages", "punitive damages",
    "liquidated damages",
    "severability", "entire agreement", "amendment",
    "assignment", "survival", "notices",
]

# Known US states and common jurisdictions
JURISDICTIONS = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California",
    "Colorado", "Connecticut", "Delaware", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas",
    "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts",
    "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana",
    "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma",
    "Oregon", "Pennsylvania", "Rhode Island", "South Carolina",
    "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
    "District of Columbia",
    # Common international
    "United States", "United Kingdom", "Canada", "European Union",
    "North America", "England", "Wales",
]


# ── Extraction Functions ─────────────────────────────────────────

def _extract_with_spacy(text: str) -> list[Entity]:
    """
    Use spaCy's built-in NER to extract standard entities.

    spaCy is good at: ORG (companies), PERSON (people), DATE,
    MONEY, GPE (countries/states/cities).
    """
    nlp = _get_nlp()
    doc = nlp(text)
    entities = []

    # Map spaCy labels to our labels
    label_map = {
        "ORG": "PARTY",
        "PERSON": "PARTY",
        "DATE": "DATE",
        "MONEY": "MONEY",
        "GPE": "JURISDICTION",  # Geopolitical entity
    }

    for ent in doc.ents:
        our_label = label_map.get(ent.label_)
        if our_label:
            # Get some surrounding context (50 chars each side)
            ctx_start = max(0, ent.start_char - 50)
            ctx_end = min(len(text), ent.end_char + 50)

            entities.append(Entity(
                text=ent.text,
                label=our_label,
                start=ent.start_char,
                end=ent.end_char,
                source="spacy",
                context=text[ctx_start:ctx_end],
            ))

    return entities


def _extract_with_regex(text: str) -> list[Entity]:
    """
    Use regex patterns to catch legal-specific entities
    that spaCy's general model misses.
    """
    entities = []

    # ── Durations ──
    for pattern in DURATION_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            entities.append(Entity(
                text=match.group(),
                label="DURATION",
                start=match.start(),
                end=match.end(),
                source="regex",
            ))

    # ── Percentages ──
    for pattern in PERCENTAGE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            entities.append(Entity(
                text=match.group(),
                label="PERCENTAGE",
                start=match.start(),
                end=match.end(),
                source="regex",
            ))

    # ── Money (supplementing spaCy) ──
    for pattern in MONEY_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            entities.append(Entity(
                text=match.group(),
                label="MONEY",
                start=match.start(),
                end=match.end(),
                source="regex",
            ))

    # ── Legal Terms ──
    text_lower = text.lower()
    for term in LEGAL_TERMS:
        # Find all occurrences of this term
        start = 0
        while True:
            idx = text_lower.find(term.lower(), start)
            if idx == -1:
                break
            entities.append(Entity(
                text=text[idx:idx + len(term)],
                label="LEGAL_TERM",
                start=idx,
                end=idx + len(term),
                source="regex",
            ))
            start = idx + len(term)

    # ── Jurisdictions (supplementing spaCy) ──
    for jurisdiction in JURISDICTIONS:
        for match in re.finditer(
            r'\b' + re.escape(jurisdiction) + r'\b',
            text,
            re.IGNORECASE
        ):
            entities.append(Entity(
                text=match.group(),
                label="JURISDICTION",
                start=match.start(),
                end=match.end(),
                source="regex",
            ))

    return entities


def _deduplicate_entities(entities: list[Entity]) -> list[Entity]:
    """
    Remove duplicate entities (same text at same position).
    Prefer spaCy results over regex when they overlap.
    """
    # Sort by position, then prefer spaCy
    entities.sort(key=lambda e: (e.start, 0 if e.source == "spacy" else 1))

    deduplicated = []
    seen_spans = set()

    for entity in entities:
        # Create a key from position and label
        span_key = (entity.start, entity.end, entity.label)

        # Check if this span overlaps with any we've already kept
        overlaps = False
        for seen_start, seen_end, seen_label in seen_spans:
            if (entity.start < seen_end and entity.end > seen_start
                    and entity.label == seen_label):
                overlaps = True
                break

        if not overlaps:
            deduplicated.append(entity)
            seen_spans.add(span_key)

    return deduplicated


def _organize_entities(entities: list[Entity]) -> ContractEntities:
    """Sort entities into their respective categories."""
    result = ContractEntities()

    for entity in entities:
        if entity.label == "PARTY":
            result.parties.append(entity)
        elif entity.label == "DATE":
            result.dates.append(entity)
        elif entity.label == "DURATION":
            result.durations.append(entity)
        elif entity.label == "MONEY":
            result.money.append(entity)
        elif entity.label == "JURISDICTION":
            result.jurisdictions.append(entity)
        elif entity.label == "PERCENTAGE":
            result.percentages.append(entity)
        elif entity.label == "LEGAL_TERM":
            result.legal_terms.append(entity)

    return result


# ── Main Functions (what the rest of the app calls) ──────────────

def extract_entities(text: str) -> ContractEntities:
    """
    Extract all legal entities from a piece of text.

    Runs spaCy NER + custom regex patterns, deduplicates,
    and returns organized results.

    Args:
        text: Contract text (can be full doc or single clause).

    Returns:
        ContractEntities with all extracted entities organized by type.
    """
    # Run both extraction methods
    spacy_entities = _extract_with_spacy(text)
    regex_entities = _extract_with_regex(text)

    # Combine and deduplicate
    all_entities = spacy_entities + regex_entities
    deduplicated = _deduplicate_entities(all_entities)

    # Organize by category
    return _organize_entities(deduplicated)


def extract_entities_from_chunks(chunks: list) -> dict:
    """
    Process a list of ClauseChunks and extract entities from each.

    Returns a dict mapping chunk_index to ContractEntities,
    plus an aggregated view across all chunks.

    Args:
        chunks: List of ClauseChunk objects from clause_chunker.py

    Returns:
        {
            "by_chunk": {0: ContractEntities, 1: ContractEntities, ...},
            "aggregated": ContractEntities  (merged from all chunks)
        }
    """
    by_chunk = {}
    all_entities = []

    for chunk in chunks:
        chunk_entities = extract_entities(chunk.text)
        by_chunk[chunk.chunk_index] = chunk_entities
        all_entities.extend(chunk_entities.all_entities)

    # Build aggregated view
    aggregated = _organize_entities(_deduplicate_entities(all_entities))

    return {
        "by_chunk": by_chunk,
        "aggregated": aggregated,
    }


def get_contract_summary(entities: ContractEntities) -> dict:
    """
    Generate a human-readable summary of key contract details.

    This is what you'd show at the top of a risk report:
    "Contract between X and Y, effective DATE, governed by LAW..."
    """
    return {
        "parties": entities.unique_values("parties"),
        "key_dates": entities.unique_values("dates"),
        "time_periods": entities.unique_values("durations"),
        "financial_values": entities.unique_values("money"),
        "jurisdictions": entities.unique_values("jurisdictions"),
        "key_legal_concepts": entities.unique_values("legal_terms"),
        "entity_counts": entities.summary,
    }


# ── Direct Testing ───────────────────────────────────────────────

if __name__ == "__main__":
    from rich import print as rprint
    from rich.table import Table
    from rich.panel import Panel

    sample = """
    This Master Services Agreement is entered into as of January 15, 2025
    by and between Nexus Dynamics Inc., a Delaware corporation ("Company"),
    and Brightpath Solutions LLC, a California limited liability company
    ("Service Provider").

    This Agreement shall automatically renew for successive twelve (12) month
    periods unless either party provides written notice at least ninety (90)
    days prior to expiration.

    Service Provider's liability shall be unlimited and uncapped. Company's
    total liability shall not exceed $150,000.

    Service Provider shall not compete within North America for a period of
    thirty-six (36) months following termination. Late payments accrue
    interest at 1.5% per month.

    This Agreement shall be governed by the laws of the State of Delaware.
    Disputes shall be resolved through binding arbitration.
    """

    entities = extract_entities(sample)
    summary = get_contract_summary(entities)

    # Display results
    rprint(Panel("[bold]Contract NER Results[/bold]", style="blue"))

    for label, values in summary.items():
        if label == "entity_counts":
            continue
        if values:
            rprint(f"\n[bold yellow]{label.upper()}:[/bold yellow]")
            for v in values:
                rprint(f"  • {v}")

    rprint(f"\n[bold green]Entity Counts:[/bold green]")
    for k, v in summary["entity_counts"].items():
        rprint(f"  {k:<15} {v}")