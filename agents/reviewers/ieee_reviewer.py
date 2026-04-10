"""IEEE Paper Reviewer agent – validates full IEEE conference/journal papers."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from agents.reviewers.prompts import IEEE_REVIEW_PROMPT

if TYPE_CHECKING:
    from agents.token_engine.engine import TokenBudgetEngine

logger = logging.getLogger(__name__)


class IEEEReviewer:
    """Reviews IEEE papers for formatting, citations, novelty, and logic.

    Uses Opus for deep reasoning on quality assessment.
    """

    AGENT_TYPE = "reviewer_ieee"

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
        revision_number: int = 1,
    ) -> dict[str, Any]:
        """Run a full peer review on an IEEE paper.

        Returns structured JSON review with verdict, issues, and summary.
        """
        prompt = IEEE_REVIEW_PROMPT.format(
            paper_content=paper_content,
            bib_content=bib_content,
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
            logger.error("Failed to parse IEEE review response")
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
