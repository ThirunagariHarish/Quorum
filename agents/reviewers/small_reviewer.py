"""Small Paper Reviewer agent – validates workshop and poster papers."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from agents.reviewers.prompts import SMALL_REVIEW_PROMPT

if TYPE_CHECKING:
    from agents.token_engine.engine import TokenBudgetEngine

logger = logging.getLogger(__name__)

PAPER_TYPE_REVIEW_CONFIG = {
    "workshop_4page": {"page_limit": 4, "ref_min": 8},
    "poster_2page": {"page_limit": 2, "ref_min": 5},
}


class SmallPaperReviewer:
    """Reviews short workshop/poster papers using Sonnet."""

    AGENT_TYPE = "reviewer_small"

    def __init__(
        self,
        token_engine: TokenBudgetEngine,
        *,
        agent_id: str | None = None,
    ) -> None:
        self.token_engine = token_engine
        self.agent_id = agent_id

    async def review(
        self,
        paper_content: str,
        bib_content: str = "",
        paper_type: str = "workshop_4page",
        revision_number: int = 1,
    ) -> dict[str, Any]:
        config = PAPER_TYPE_REVIEW_CONFIG.get(
            paper_type, PAPER_TYPE_REVIEW_CONFIG["workshop_4page"]
        )

        prompt = SMALL_REVIEW_PROMPT.format(
            paper_type=paper_type,
            paper_content=paper_content,
            bib_content=bib_content,
            page_limit=config["page_limit"],
            ref_min=config["ref_min"],
            revision_number=revision_number,
        )

        result = await self.token_engine.execute_with_budget(
            agent_type=self.AGENT_TYPE,
            task_phase="review",
            prompt=prompt,
            agent_id=self.agent_id,
            max_tokens=4096,
        )

        try:
            review_data = json.loads(result["text"])
        except (json.JSONDecodeError, KeyError):
            logger.error("Failed to parse small paper review response")
            review_data = {
                "verdict": "revise",
                "overall_quality": 5,
                "issues": [
                    {
                        "severity": "major",
                        "category": "system",
                        "location": "N/A",
                        "description": "Review agent produced unparseable output",
                        "suggestion": "Re-run review",
                    }
                ],
                "summary": "Review could not be completed. Please re-run.",
                "revision_number": revision_number,
                "max_revisions": 3,
            }

        review_data["reviewer_agent"] = self.AGENT_TYPE
        review_data["model_used"] = result.get("model", "")
        return review_data
