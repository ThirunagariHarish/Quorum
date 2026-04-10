"""Blog Article Reviewer agent – validates code correctness, tone, and readability."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from agents.reviewers.prompts import BLOG_REVIEW_PROMPT

if TYPE_CHECKING:
    from agents.token_engine.engine import TokenBudgetEngine

logger = logging.getLogger(__name__)


class BlogReviewer:
    """Reviews blog articles using Haiku for efficient pattern matching."""

    AGENT_TYPE = "reviewer_blog"

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
        article_content: str,
        part_number: int = 1,
        revision_number: int = 1,
    ) -> dict[str, Any]:
        prompt = BLOG_REVIEW_PROMPT.format(
            article_content=article_content,
            part_number=part_number,
            revision_number=revision_number,
        )

        result = await self.token_engine.execute_with_budget(
            agent_type=self.AGENT_TYPE,
            task_phase="review",
            prompt=prompt,
            agent_id=self.agent_id,
            max_tokens=2048,
        )

        try:
            review_data = json.loads(result["text"])
        except (json.JSONDecodeError, KeyError):
            logger.error("Failed to parse blog review response")
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
