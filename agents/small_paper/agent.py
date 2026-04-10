"""Small Paper Agent – generates 2-4 page workshop and poster papers."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from agents.small_paper.prompts import (
    SMALL_PAPER_OUTLINE_PROMPT,
    SMALL_PAPER_SELF_CHECK_PROMPT,
    SMALL_PAPER_SYSTEM_PROMPT,
)

if TYPE_CHECKING:
    from agents.shared.latex import LaTeXCompiler
    from agents.shared.search import UnifiedSearch
    from agents.shared.storage import StorageService
    from agents.token_engine.engine import TokenBudgetEngine

logger = logging.getLogger(__name__)

PAPER_TYPE_CONFIG = {
    "workshop_4page": {
        "page_limit": 4,
        "abstract_limit": 150,
        "ref_min": 8,
        "ref_max": 15,
    },
    "poster_2page": {
        "page_limit": 2,
        "abstract_limit": 100,
        "ref_min": 5,
        "ref_max": 10,
    },
}


class SmallPaperAgent:
    """Generates short workshop (4-page) and poster (2-page) IEEE papers."""

    AGENT_TYPE = "small_paper"

    def __init__(
        self,
        token_engine: TokenBudgetEngine,
        search_client: UnifiedSearch,
        storage: StorageService,
        latex_compiler: LaTeXCompiler,
        *,
        agent_id: str | None = None,
    ) -> None:
        self.token_engine = token_engine
        self.search = search_client
        self.storage = storage
        self.latex = latex_compiler
        self.agent_id = agent_id

    async def generate_paper(
        self,
        topic: str,
        paper_type: str = "workshop_4page",
        reference_papers: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Full pipeline: literature scan → outline → write → self-check."""
        reference_papers = reference_papers or []
        config = PAPER_TYPE_CONFIG.get(paper_type, PAPER_TYPE_CONFIG["workshop_4page"])
        logger.info("Small paper generation: %s (%s)", topic, paper_type)

        lit_results = await self._literature_scan(topic)

        outline = await self._generate_outline(
            topic, paper_type, reference_papers + lit_results
        )

        paper_result = await self._write_paper(
            topic, paper_type, outline, reference_papers + lit_results
        )

        check_result = await self._self_check(
            paper_result.get("tex_content", ""), paper_type, config
        )
        paper_result["self_check"] = check_result

        tex_content = paper_result.get("tex_content", "")
        bib_content = paper_result.get("bib_content", "")

        if tex_content:
            compilation = self.latex.compile(tex_content, bib_content)
            paper_result["compilation"] = {
                "success": compilation.success,
                "errors": compilation.errors,
            }
            if compilation.pdf_bytes:
                paper_result["pdf_bytes"] = compilation.pdf_bytes

        return paper_result

    async def _literature_scan(self, topic: str) -> list[dict[str, Any]]:
        papers = await self.search.search(topics=[topic], days_back=90, max_per_source=5)
        logger.info("Literature scan found %d papers", len(papers))
        return papers

    async def _generate_outline(
        self,
        topic: str,
        paper_type: str,
        reference_papers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ref_summary = json.dumps(
            [{"title": p.get("title", ""), "abstract": (p.get("abstract") or "")[:150]} for p in reference_papers[:10]],
            indent=2,
        )

        prompt = SMALL_PAPER_OUTLINE_PROMPT.format(
            paper_type=paper_type,
            topic=topic,
            reference_papers=ref_summary,
        )

        result = await self.token_engine.execute_with_budget(
            agent_type=self.AGENT_TYPE,
            task_phase="literature_scan",
            prompt=prompt,
            agent_id=self.agent_id,
        )

        try:
            return json.loads(result["text"])
        except (json.JSONDecodeError, KeyError):
            return {"title": topic, "contribution": "", "sections": []}

    async def _write_paper(
        self,
        topic: str,
        paper_type: str,
        outline: dict[str, Any],
        reference_papers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ref_json = json.dumps(
            [{"title": p.get("title", ""), "doi": p.get("doi", "")} for p in reference_papers[:15]]
        )

        system_prompt = SMALL_PAPER_SYSTEM_PROMPT.format(
            paper_type=paper_type,
            topic=topic,
            reference_papers=ref_json,
        )

        prompt = (
            f"Write the complete paper based on this outline:\n"
            f"{json.dumps(outline, indent=2)}\n\n"
            f"Output the paper as two fenced code blocks: ```latex for main.tex and "
            f"```bibtex for references.bib."
        )

        result = await self.token_engine.execute_with_budget(
            agent_type=self.AGENT_TYPE,
            task_phase="paper_writing",
            prompt=prompt,
            system_prompt=system_prompt,
            agent_id=self.agent_id,
            max_tokens=8192,
        )

        text = result["text"]
        tex_content = self._extract_block(text, "latex") or self._extract_block(text, "tex") or ""
        bib_content = self._extract_block(text, "bibtex") or self._extract_block(text, "bib") or ""

        return {
            "tex_content": tex_content,
            "bib_content": bib_content,
            "raw_response": text,
            "model": result["model"],
        }

    async def _self_check(
        self, paper_content: str, paper_type: str, config: dict[str, int]
    ) -> dict[str, Any]:
        if not paper_content:
            return {"passes": False, "issues": ["No paper content generated"]}

        prompt = SMALL_PAPER_SELF_CHECK_PROMPT.format(
            paper_type=paper_type,
            paper_content=paper_content[:6000],
            page_limit=config["page_limit"],
            abstract_limit=config["abstract_limit"],
            ref_min=config["ref_min"],
            ref_max=config["ref_max"],
        )

        result = await self.token_engine.execute_with_budget(
            agent_type=self.AGENT_TYPE,
            task_phase="self_check",
            prompt=prompt,
            agent_id=self.agent_id,
        )

        try:
            return json.loads(result["text"])
        except (json.JSONDecodeError, KeyError):
            return {"passes": True, "issues": [], "suggestions": []}

    @staticmethod
    def _extract_block(text: str, lang: str) -> str:
        pattern = rf"```{lang}\s*\n(.*?)```"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""
