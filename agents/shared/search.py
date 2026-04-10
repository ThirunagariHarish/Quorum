"""Unified paper search across OpenAlex, arXiv, Semantic Scholar, and IEEE Xplore."""

from __future__ import annotations

import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def reconstruct_abstract(inverted_index: dict[str, list[int]]) -> str:
    """Rebuild plain text from OpenAlex inverted-index abstract format."""
    if not inverted_index:
        return ""
    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(word for _, word in word_positions)


def _title_similarity(t1: str, t2: str) -> float:
    """Jaccard similarity on lowercased word sets."""
    s1 = set(t1.lower().split())
    s2 = set(t2.lower().split())
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------

class OpenAlexClient:
    """Client for the OpenAlex scholarly works API (free, no key required)."""

    BASE_URL = "https://api.openalex.org"

    def __init__(self, email: str | None = None) -> None:
        self.email = email

    async def search_papers(
        self,
        query: str,
        from_date: str | None = None,
        sort_by: str = "cited_by_count:desc",
        per_page: int = 25,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "search": query,
            "sort": sort_by,
            "per_page": per_page,
        }
        if from_date:
            params["filter"] = f"from_publication_date:{from_date}"
        if self.email:
            params["mailto"] = self.email

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/works", params=params, timeout=30
            )
            response.raise_for_status()
            data = response.json()

        return [self._normalize(work) for work in data.get("results", [])]

    async def search_trending(
        self, topics: list[str], days_back: int = 7
    ) -> list[dict[str, Any]]:
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        all_results: list[dict[str, Any]] = []
        for topic in topics:
            results = await self.search_papers(
                query=topic, from_date=from_date, sort_by="publication_date:desc"
            )
            all_results.extend(results)
        return all_results

    def _normalize(self, work: dict) -> dict[str, Any]:
        abstract_raw = work.get("abstract_inverted_index", {})
        abstract = reconstruct_abstract(abstract_raw) if isinstance(abstract_raw, dict) else ""

        primary_loc = work.get("primary_location") or {}
        source = primary_loc.get("source") or {}

        return {
            "source": "openalex",
            "id": work.get("id", ""),
            "doi": work.get("doi", ""),
            "title": work.get("title", ""),
            "abstract": abstract,
            "authors": [
                a.get("author", {}).get("display_name", "")
                for a in work.get("authorships", [])
            ],
            "publication_date": work.get("publication_date", ""),
            "venue": source.get("display_name", ""),
            "citation_count": work.get("cited_by_count", 0),
            "open_access": work.get("open_access", {}).get("is_oa", False),
            "url": primary_loc.get("landing_page_url", ""),
        }


# ---------------------------------------------------------------------------
# arXiv
# ---------------------------------------------------------------------------

class ArxivClient:
    """Client for the arXiv API (free, rate-limited to 1 req/3s)."""

    BASE_URL = "http://export.arxiv.org/api/query"

    CATEGORIES: dict[str, str] = {
        "blockchain": "cs.CR",
        "autonomous_vehicles": "cs.RO",
        "ai": "cs.AI",
        "machine_learning": "cs.LG",
        "distributed": "cs.DC",
    }

    async def search_papers(
        self,
        query: str,
        categories: list[str] | None = None,
        max_results: int = 25,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
    ) -> list[dict[str, Any]]:
        search_query = f'all:"{query}"'
        if categories:
            cat_filter = " OR ".join(f"cat:{c}" for c in categories)
            search_query = f"({search_query}) AND ({cat_filter})"

        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()

        return self._parse_atom_feed(response.text)

    async def search_trending(
        self, topics: list[str], categories: list[str] | None = None
    ) -> list[dict[str, Any]]:
        all_results: list[dict[str, Any]] = []
        for topic in topics:
            await asyncio.sleep(3)  # arXiv rate limit
            results = await self.search_papers(
                query=topic, categories=categories, max_results=10
            )
            all_results.extend(results)
        return all_results

    def _parse_atom_feed(self, xml_text: str) -> list[dict[str, Any]]:
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        root = ET.fromstring(xml_text)
        results: list[dict[str, Any]] = []

        for entry in root.findall("atom:entry", ns):
            id_elem = entry.find("atom:id", ns)
            if id_elem is None or id_elem.text is None:
                continue
            arxiv_id = id_elem.text.split("/abs/")[-1]

            authors = [
                author.find("atom:name", ns).text  # type: ignore[union-attr]
                for author in entry.findall("atom:author", ns)
                if author.find("atom:name", ns) is not None
            ]

            cats = [
                cat.get("term", "")
                for cat in entry.findall("arxiv:primary_category", ns)
            ]

            title_elem = entry.find("atom:title", ns)
            summary_elem = entry.find("atom:summary", ns)
            published_elem = entry.find("atom:published", ns)

            results.append({
                "source": "arxiv",
                "id": f"arxiv:{arxiv_id}",
                "doi": "",
                "title": (title_elem.text or "").strip().replace("\n", " ") if title_elem is not None else "",
                "abstract": (summary_elem.text or "").strip().replace("\n", " ") if summary_elem is not None else "",
                "authors": authors,
                "publication_date": (published_elem.text or "")[:10] if published_elem is not None else "",
                "venue": f"arXiv {', '.join(cats)}",
                "citation_count": 0,
                "open_access": True,
                "url": f"https://arxiv.org/abs/{arxiv_id}",
            })

        return results


# ---------------------------------------------------------------------------
# Semantic Scholar
# ---------------------------------------------------------------------------

class SemanticScholarClient:
    """Client for the Semantic Scholar Academic Graph API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    DEFAULT_FIELDS = (
        "title,abstract,authors,year,venue,citationCount,"
        "externalIds,openAccessPdf,publicationDate"
    )

    def __init__(self, api_key: str | None = None) -> None:
        self.headers: dict[str, str] = {}
        if api_key:
            self.headers["x-api-key"] = api_key

    async def search_papers(
        self,
        query: str,
        year: str | None = None,
        fields: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "query": query,
            "fields": fields or self.DEFAULT_FIELDS,
            "limit": limit,
        }
        if year:
            params["year"] = year

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/paper/search",
                params=params,
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

        return [self._normalize(paper) for paper in data.get("data", [])]

    async def get_paper_by_doi(self, doi: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/paper/DOI:{doi}",
                params={"fields": "title,authors,year,venue,citationCount"},
                headers=self.headers,
                timeout=15,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return self._normalize(response.json())

    async def verify_citation(self, title: str) -> dict[str, Any] | None:
        results = await self.search_papers(query=title, limit=3)
        for r in results:
            if _title_similarity(title, r.get("title", "")) > 0.85:
                return r
        return None

    def _normalize(self, paper: dict) -> dict[str, Any]:
        external_ids = paper.get("externalIds") or {}
        authors = paper.get("authors") or []

        return {
            "source": "semantic_scholar",
            "id": paper.get("paperId", ""),
            "doi": external_ids.get("DOI", ""),
            "title": paper.get("title", ""),
            "abstract": paper.get("abstract") or "",
            "authors": [a.get("name", "") for a in authors],
            "publication_date": paper.get("publicationDate") or "",
            "venue": paper.get("venue") or "",
            "citation_count": paper.get("citationCount", 0),
            "open_access": bool(paper.get("openAccessPdf")),
            "url": f"https://api.semanticscholar.org/CorpusID:{paper.get('paperId', '')}",
        }


# ---------------------------------------------------------------------------
# IEEE Xplore
# ---------------------------------------------------------------------------

class IEEEXploreClient:
    """Client for the IEEE Xplore developer API."""

    BASE_URL = "https://ieeexploreapi.ieee.org/api/v1/search/articles"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def search_papers(
        self,
        query: str,
        start_year: int | None = None,
        end_year: int | None = None,
        content_type: str | None = None,
        max_records: int = 25,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "querytext": query,
            "apikey": self.api_key,
            "max_records": max_records,
            "sort_field": "article_date",
            "sort_order": "desc",
        }
        if start_year:
            params["start_year"] = start_year
        if end_year:
            params["end_year"] = end_year
        if content_type:
            params["content_type"] = content_type

        async with httpx.AsyncClient() as client:
            response = await client.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

        return [self._normalize(a) for a in data.get("articles", [])]

    def _normalize(self, article: dict) -> dict[str, Any]:
        authors_block = article.get("authors", {}).get("authors", [])
        return {
            "source": "ieee_xplore",
            "id": f"ieee:{article.get('article_number', '')}",
            "doi": article.get("doi", ""),
            "title": article.get("title", ""),
            "abstract": article.get("abstract", ""),
            "authors": [a.get("full_name", "") for a in authors_block],
            "publication_date": article.get("publication_date", ""),
            "venue": article.get("publication_title", ""),
            "citation_count": article.get("citing_paper_count", 0),
            "open_access": article.get("access_type", "") == "OPEN_ACCESS",
            "url": article.get("html_url", ""),
        }


# ---------------------------------------------------------------------------
# Unified search
# ---------------------------------------------------------------------------

class UnifiedSearch:
    """Queries all configured APIs in parallel, deduplicates by DOI/title."""

    def __init__(
        self,
        openalex: OpenAlexClient,
        arxiv: ArxivClient,
        semantic_scholar: SemanticScholarClient,
        ieee_xplore: IEEEXploreClient | None = None,
    ) -> None:
        self.sources: dict[str, Any] = {
            "openalex": openalex,
            "arxiv": arxiv,
            "semantic_scholar": semantic_scholar,
        }
        if ieee_xplore:
            self.sources["ieee_xplore"] = ieee_xplore

    async def search(
        self,
        topics: list[str],
        days_back: int = 7,
        max_per_source: int = 15,
    ) -> list[dict[str, Any]]:
        tasks: list[Any] = []
        for topic in topics:
            for source_name, client in self.sources.items():
                if source_name == "openalex":
                    from_date = (
                        datetime.now() - timedelta(days=days_back)
                    ).strftime("%Y-%m-%d")
                    tasks.append(
                        client.search_papers(
                            query=topic, from_date=from_date, per_page=max_per_source
                        )
                    )
                elif source_name == "arxiv":
                    tasks.append(
                        client.search_papers(query=topic, max_results=max_per_source)
                    )
                elif source_name == "semantic_scholar":
                    tasks.append(
                        client.search_papers(query=topic, limit=max_per_source)
                    )
                elif source_name == "ieee_xplore":
                    tasks.append(
                        client.search_papers(query=topic, max_records=max_per_source)
                    )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_papers: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Search source error: %s", result)
                continue
            all_papers.extend(result)

        return self._deduplicate(all_papers)

    @staticmethod
    def _deduplicate(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen_dois: set[str] = set()
        seen_titles: set[str] = set()
        unique: list[dict[str, Any]] = []

        for paper in papers:
            doi = (paper.get("doi") or "").strip()
            title_key = (paper.get("title") or "").lower().strip()

            if doi and doi in seen_dois:
                continue
            if title_key and title_key in seen_titles:
                continue

            if doi:
                seen_dois.add(doi)
            if title_key:
                seen_titles.add(title_key)
            unique.append(paper)

        return unique
