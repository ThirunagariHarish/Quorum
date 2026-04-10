"""Research Orchestrator – discovers topics, ranks them, and delegates to sub-agents."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from agents.orchestrator.prompts import (
    DELEGATION_PROMPT,
    ORCHESTRATOR_SYSTEM_PROMPT,
    TOPIC_RANKING_PROMPT,
)

if TYPE_CHECKING:
    from agents.shared.notifications import TelegramNotifier
    from agents.shared.search import UnifiedSearch
    from agents.shared.storage import StorageService
    from agents.token_engine.engine import TokenBudgetEngine

logger = logging.getLogger(__name__)


class ResearchOrchestrator:
    """Primary agent: discovers trending topics and dispatches work to sub-agents."""

    AGENT_TYPE = "orchestrator"

    def __init__(
        self,
        token_engine: TokenBudgetEngine,
        search_client: UnifiedSearch,
        notifier: TelegramNotifier,
        storage: StorageService,
        *,
        agent_id: str | None = None,
    ) -> None:
        self.token_engine = token_engine
        self.search = search_client
        self.notifier = notifier
        self.storage = storage
        self.agent_id = agent_id

    async def run_discovery_cycle(
        self,
        niche_topics: list[str],
        user_settings: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Run a full discovery + ranking cycle.

        1. Search all APIs for recent papers matching niche topics
        2. Ask Claude to rank them
        3. Send top-5 suggestions to user via Telegram
        """
        logger.info("Starting discovery cycle for topics: %s", niche_topics)

        papers = await self.search.search(topics=niche_topics, days_back=2)
        logger.info("Discovered %d papers across all sources", len(papers))

        if not papers:
            await self.notifier.send_message(
                "📋 Quorum: No trending topics discovered in this cycle."
            )
            return []

        papers_json = json.dumps(
            [
                {
                    "title": p.get("title", ""),
                    "abstract": (p.get("abstract") or "")[:300],
                    "authors": p.get("authors", [])[:3],
                    "publication_date": p.get("publication_date", ""),
                    "citation_count": p.get("citation_count", 0),
                    "venue": p.get("venue", ""),
                    "source": p.get("source", ""),
                }
                for p in papers[:30]
            ],
            indent=2,
        )

        ranking_prompt = TOPIC_RANKING_PROMPT.format(
            papers_json=papers_json,
            niche_topics=", ".join(niche_topics),
        )

        result = await self.token_engine.execute_with_budget(
            agent_type=self.AGENT_TYPE,
            task_phase="topic_ranking",
            prompt=ranking_prompt,
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT.format(
                niche_topics=", ".join(niche_topics)
            ),
            agent_id=self.agent_id,
        )

        try:
            ranked_topics = json.loads(result["text"])
        except (json.JSONDecodeError, KeyError):
            logger.error("Failed to parse ranking response: %s", result.get("text", "")[:200])
            ranked_topics = []

        if ranked_topics:
            msg_text, buttons = self.notifier.format_topic_suggestions(ranked_topics)
            await self.notifier.send_with_inline_keyboard(msg_text, buttons)

        return ranked_topics

    async def process_topic_selection(
        self, selected_topics: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Create agent tasks for user-selected topics and dispatch to sub-agents."""
        topics_json = json.dumps(selected_topics, indent=2)
        prompt = DELEGATION_PROMPT.format(selected_topics=topics_json)

        result = await self.token_engine.execute_with_budget(
            agent_type=self.AGENT_TYPE,
            task_phase="task_delegation",
            prompt=prompt,
            agent_id=self.agent_id,
        )

        try:
            tasks = json.loads(result["text"])
        except (json.JSONDecodeError, KeyError):
            logger.error("Failed to parse delegation response")
            tasks = []

        logger.info("Created %d agent tasks from selection", len(tasks))
        return tasks
