"""Citation parsing, verification, and formatting utilities."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

import bibtexparser

if TYPE_CHECKING:
    from agents.shared.search import SemanticScholarClient

logger = logging.getLogger(__name__)


def parse_bibtex(bib_content: str) -> list[dict[str, Any]]:
    """Parse BibTeX content into a list of entry dicts (bibtexparser v1 API)."""
    parser = bibtexparser.bparser.BibTexParser(common_strings=True)
    bib_db = bibtexparser.loads(bib_content, parser=parser)
    entries: list[dict[str, Any]] = []
    for entry in bib_db.entries:
        entries.append({
            "key": entry.get("ID", ""),
            "type": entry.get("ENTRYTYPE", ""),
            "title": entry.get("title", ""),
            "author": entry.get("author", ""),
            "year": entry.get("year", ""),
            "doi": entry.get("doi", ""),
            "booktitle": entry.get("booktitle", ""),
            "journal": entry.get("journal", ""),
            "pages": entry.get("pages", ""),
        })
    return entries


async def verify_citation(
    title: str, semantic_scholar_client: SemanticScholarClient
) -> dict[str, Any] | None:
    """Attempt to verify a citation by title via Semantic Scholar search.

    Returns the matched paper dict if found (>85 % Jaccard title similarity),
    otherwise ``None``.
    """
    return await semantic_scholar_client.verify_citation(title)


async def verify_all_citations(
    bib_content: str, ss_client: SemanticScholarClient
) -> dict[str, Any]:
    """Verify every entry in a BibTeX string.

    Returns a report dict::

        {
            "total": int,
            "verified": int,
            "unverified": int,
            "verification_rate": float,
            "results": [{"key": ..., "title": ..., "verified": bool, "match": ...}, ...]
        }
    """
    entries = parse_bibtex(bib_content)
    results: list[dict[str, Any]] = []
    verified_count = 0

    for entry in entries:
        title = entry.get("title", "")
        if not title:
            results.append({"key": entry["key"], "title": "", "verified": False, "match": None})
            continue

        match = await verify_citation(title, ss_client)
        is_verified = match is not None
        if is_verified:
            verified_count += 1

        results.append({
            "key": entry["key"],
            "title": title,
            "verified": is_verified,
            "match": match,
        })

    total = len(entries)
    return {
        "total": total,
        "verified": verified_count,
        "unverified": total - verified_count,
        "verification_rate": (verified_count / total) if total else 0.0,
        "results": results,
    }


def format_ieee_citation(paper: dict[str, Any]) -> str:
    """Format a normalized paper dict as an IEEE-style BibTeX ``@inproceedings`` entry."""
    authors = paper.get("authors", [])
    author_str = " and ".join(authors) if authors else "Unknown"

    title = paper.get("title", "Untitled")
    venue = paper.get("venue", "")
    year = paper.get("publication_date", "")[:4] or "2026"
    doi = paper.get("doi", "")

    key = re.sub(r"[^a-z0-9]", "", (authors[0].split()[-1] if authors else "unknown").lower())
    first_word = re.sub(r"[^a-z0-9]", "", title.split()[0].lower()) if title.split() else "paper"
    bib_key = f"{key}{year}{first_word}"

    lines = [
        f"@inproceedings{{{bib_key},",
        f"  author    = {{{author_str}}},",
        f"  title     = {{{title}}},",
    ]
    if venue:
        lines.append(f"  booktitle = {{{venue}}},")
    lines.append(f"  year      = {{{year}}},")
    if doi:
        lines.append(f"  doi       = {{{doi}}},")
    lines.append("}")

    return "\n".join(lines)
