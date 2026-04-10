"""Blog Implementation Agent – generates 3-part technical article series."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from agents.blog.prompts import BLOG_OUTLINE_PROMPT, BLOG_SYSTEM_PROMPT

if TYPE_CHECKING:
    from agents.shared.storage import StorageService
    from agents.token_engine.engine import TokenBudgetEngine

logger = logging.getLogger(__name__)


class BlogAgent:
    """Generates implementation-focused blog series (3 parts) in dev.to Markdown."""

    AGENT_TYPE = "blog"

    def __init__(
        self,
        token_engine: TokenBudgetEngine,
        storage: StorageService,
        *,
        agent_id: str | None = None,
    ) -> None:
        self.token_engine = token_engine
        self.storage = storage
        self.agent_id = agent_id

    async def generate_series(
        self, topic: str
    ) -> list[dict[str, Any]]:
        """Generate a complete 3-part blog series.

        Returns a list of 3 dicts, each containing:
            markdown, part_number, subtitle, model
        """
        logger.info("Blog series generation started: %s", topic)

        outline = await self._create_outline(topic)
        series_title = outline.get("series_title", topic)
        parts = outline.get("parts", [])

        articles: list[dict[str, Any]] = []

        for idx in range(3):
            part_number = idx + 1
            part_info = parts[idx] if idx < len(parts) else {}

            article = await self._write_article(
                topic=topic,
                series_title=series_title,
                part_number=part_number,
                part_info=part_info,
                previous_parts=[a.get("markdown", "") for a in articles],
            )
            articles.append(article)

            logger.info(
                "Completed Part %d/%d (%d chars)",
                part_number,
                3,
                len(article.get("markdown", "")),
            )

        return articles

    async def _create_outline(self, topic: str) -> dict[str, Any]:
        prompt = BLOG_OUTLINE_PROMPT.format(topic=topic)

        result = await self.token_engine.execute_with_budget(
            agent_type=self.AGENT_TYPE,
            task_phase="outline",
            prompt=prompt,
            agent_id=self.agent_id,
        )

        try:
            return json.loads(result["text"])
        except (json.JSONDecodeError, KeyError):
            logger.error("Failed to parse blog outline")
            return {
                "series_title": topic,
                "tags": [],
                "parts": [
                    {"subtitle": "Problem + Architecture", "description": "", "key_sections": []},
                    {"subtitle": "Implementation + Code", "description": "", "key_sections": []},
                    {"subtitle": "Results + Improvements", "description": "", "key_sections": []},
                ],
            }

    async def _write_article(
        self,
        topic: str,
        series_title: str,
        part_number: int,
        part_info: dict[str, Any],
        previous_parts: list[str],
    ) -> dict[str, Any]:
        system_prompt = BLOG_SYSTEM_PROMPT.format(
            topic=topic,
            series_title=series_title,
            part_number=part_number,
        )

        context_parts = ""
        if previous_parts:
            summaries = [
                f"Part {i+1} summary (first 300 chars): {p[:300]}"
                for i, p in enumerate(previous_parts)
                if p
            ]
            context_parts = "\n".join(summaries)

        subtitle = part_info.get("subtitle", f"Part {part_number}")
        sections = part_info.get("key_sections", [])
        description = part_info.get("description", "")

        prompt = (
            f"Write Part {part_number} of the blog series.\n\n"
            f"Subtitle: {subtitle}\n"
            f"Description: {description}\n"
            f"Sections to cover: {json.dumps(sections)}\n\n"
        )

        if context_parts:
            prompt += f"Previous parts context:\n{context_parts}\n\n"

        prompt += (
            "Write the complete article in Markdown with dev.to front matter. "
            "Include working code blocks, Mermaid diagrams where helpful, and "
            "follow the human-tone guidelines strictly."
        )

        result = await self.token_engine.execute_with_budget(
            agent_type=self.AGENT_TYPE,
            task_phase="article_writing",
            prompt=prompt,
            system_prompt=system_prompt,
            agent_id=self.agent_id,
            max_tokens=8192,
        )

        return {
            "markdown": result["text"],
            "part_number": part_number,
            "subtitle": subtitle,
            "model": result["model"],
        }
