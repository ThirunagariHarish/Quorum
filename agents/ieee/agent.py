"""IEEE Research Agent – generates full conference/journal papers with sub-agent swarm."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from agents.ieee.prompts import (
    IEEE_ASSEMBLY_PROMPT,
    IEEE_RESEARCH_PROMPT,
    IEEE_SCOUT_PROMPT,
    IEEE_SYSTEM_PROMPT,
)

if TYPE_CHECKING:
    from agents.shared.latex import LaTeXCompiler
    from agents.shared.search import UnifiedSearch
    from agents.shared.storage import StorageService
    from agents.token_engine.engine import TokenBudgetEngine

logger = logging.getLogger(__name__)


class IEEEResearchAgent:
    """Generates full IEEE conference / journal papers.

    Pipeline:
        ideation → scout (Haiku) → full research (Sonnet) → assembly (Sonnet)
    """

    AGENT_TYPE = "ieee"

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

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    async def generate_paper(
        self,
        topic: str,
        reference_papers: list[dict[str, Any]],
        target_venue: str = "",
    ) -> dict[str, Any]:
        """End-to-end paper generation: ideate → scout → research → assemble."""
        logger.info("IEEE paper generation started: %s", topic)

        directions = await self._ideate(topic, reference_papers, target_venue)
        logger.info("Generated %d research directions", len(directions))

        scout_results = await self.spawn_scouts(directions, reference_papers)
        top_directions = [
            d
            for d in scout_results
            if d.get("recommended", False) and d.get("feasibility_score", 0) >= 6
        ][:4]

        if not top_directions:
            top_directions = sorted(
                scout_results, key=lambda x: x.get("feasibility_score", 0), reverse=True
            )[:3]

        logger.info("Proceeding with %d top directions", len(top_directions))

        research_outputs = await self.spawn_researchers(
            top_directions, topic, reference_papers, target_venue
        )

        result = await self.assemble_paper(research_outputs)

        if result.get("tex_content"):
            compilation = self.latex.compile(
                result["tex_content"],
                result.get("bib_content"),
            )
            result["compilation"] = {
                "success": compilation.success,
                "errors": compilation.errors,
            }
            if compilation.pdf_bytes:
                result["pdf_bytes"] = compilation.pdf_bytes

        return result

    # ------------------------------------------------------------------
    # Sub-phases
    # ------------------------------------------------------------------

    async def _ideate(
        self,
        topic: str,
        reference_papers: list[dict[str, Any]],
        target_venue: str,
    ) -> list[str]:
        """Generate 5-6 research extension directions (Opus)."""
        ref_summary = json.dumps(
            [{"title": p.get("title"), "abstract": (p.get("abstract") or "")[:200]} for p in reference_papers[:5]],
            indent=2,
        )

        prompt = (
            f"Given the topic '{topic}' and these reference papers:\n{ref_summary}\n\n"
            f"Target venue: {target_venue}\n\n"
            "Generate 5-6 distinct research extension directions. Each should be a different "
            "approach: methodology swap, domain transfer, scale validation, component addition, "
            "hybrid approach, or ablation study.\n\n"
            "Return a JSON array of strings, each being a concise description of one direction."
        )

        result = await self.token_engine.execute_with_budget(
            agent_type=self.AGENT_TYPE,
            task_phase="ideation",
            prompt=prompt,
            agent_id=self.agent_id,
        )

        try:
            directions = json.loads(result["text"])
            if isinstance(directions, list):
                return [str(d) for d in directions]
        except (json.JSONDecodeError, KeyError):
            logger.error("Failed to parse ideation output")

        return [f"Extend research on {topic} with alternative methodology"]

    async def spawn_scouts(
        self,
        directions: list[str | dict],
        reference_papers: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Spawn Haiku sub-agents for quick feasibility assessment."""
        results: list[dict[str, Any]] = []
        ref_summary = json.dumps(
            [{"title": p.get("title")} for p in reference_papers[:3]]
        )

        for direction in directions:
            direction_text = direction if isinstance(direction, str) else str(direction)
            prompt = IEEE_SCOUT_PROMPT.format(
                reference_paper=ref_summary,
                direction=direction_text,
            )

            result = await self.token_engine.execute_with_budget(
                agent_type=self.AGENT_TYPE,
                task_phase="scout",
                prompt=prompt,
                agent_id=self.agent_id,
            )

            try:
                scout_data = json.loads(result["text"])
                scout_data["direction"] = direction_text
                results.append(scout_data)
            except (json.JSONDecodeError, KeyError):
                results.append({
                    "direction": direction_text,
                    "feasibility_score": 5,
                    "recommended": True,
                })

        return results

    async def spawn_researchers(
        self,
        top_directions: list[dict[str, Any]],
        topic: str,
        reference_papers: list[dict[str, Any]],
        target_venue: str,
    ) -> list[dict[str, Any]]:
        """Spawn Sonnet sub-agents for full paper research per direction."""
        outputs: list[dict[str, Any]] = []
        ref_json = json.dumps(
            [{"title": p.get("title"), "doi": p.get("doi", "")} for p in reference_papers[:5]]
        )

        for direction_data in top_directions:
            direction = direction_data.get("direction", str(direction_data))

            prompt = IEEE_RESEARCH_PROMPT.format(
                topic=topic,
                direction=direction,
                reference_papers=ref_json,
                target_venue=target_venue,
            )

            result = await self.token_engine.execute_with_budget(
                agent_type=self.AGENT_TYPE,
                task_phase="full_research",
                prompt=prompt,
                agent_id=self.agent_id,
                max_tokens=8192,
            )

            outputs.append({
                "direction": direction,
                "content": result["text"],
                "model": result["model"],
                "tokens": result["input_tokens"] + result["output_tokens"],
            })

        return outputs

    async def assemble_paper(
        self, sub_agent_outputs: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Assemble the best sub-agent output into final paper."""
        outputs_summary = json.dumps(
            [
                {
                    "direction": o.get("direction", ""),
                    "content_preview": o.get("content", "")[:500],
                }
                for o in sub_agent_outputs
            ],
            indent=2,
        )

        prompt = IEEE_ASSEMBLY_PROMPT.format(sub_agent_outputs=outputs_summary)

        full_content = "\n\n---\n\n".join(
            o.get("content", "") for o in sub_agent_outputs
        )
        prompt += f"\n\nFull sub-agent outputs:\n{full_content}"

        result = await self.token_engine.execute_with_budget(
            agent_type=self.AGENT_TYPE,
            task_phase="paper_assembly",
            prompt=prompt,
            agent_id=self.agent_id,
            max_tokens=8192,
        )

        text = result["text"]

        tex_content = self._extract_block(text, "tex") or self._extract_block(text, "latex") or ""
        bib_content = self._extract_block(text, "bibtex") or self._extract_block(text, "bib") or ""

        return {
            "tex_content": tex_content,
            "bib_content": bib_content,
            "raw_response": text,
            "model": result["model"],
        }

    @staticmethod
    def _extract_block(text: str, lang: str) -> str:
        """Extract a fenced code block for the given language."""
        import re

        pattern = rf"```{lang}\s*\n(.*?)```"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""
