"""Task classification for model routing based on agent type and task phase."""

from __future__ import annotations

TASK_CLASSIFICATION: dict[tuple[str, str], str] = {
    # Orchestrator tasks
    ("orchestrator", "topic_discovery"): "standard",
    ("orchestrator", "topic_ranking"): "standard",
    ("orchestrator", "status_summary"): "simple",
    ("orchestrator", "task_delegation"): "standard",

    # IEEE Agent tasks
    ("ieee", "literature_survey"): "standard",
    ("ieee", "ideation"): "deep",
    ("ieee", "scout"): "simple",
    ("ieee", "full_research"): "standard",
    ("ieee", "paper_assembly"): "standard",
    ("ieee", "self_review"): "deep",

    # Small Paper Agent tasks
    ("small_paper", "literature_scan"): "standard",
    ("small_paper", "paper_writing"): "standard",
    ("small_paper", "self_check"): "standard",

    # Blog Agent tasks
    ("blog", "topic_research"): "standard",
    ("blog", "outline"): "standard",
    ("blog", "article_writing"): "standard",
    ("blog", "code_generation"): "simple",
    ("blog", "polish"): "standard",

    # Review Agent tasks
    ("reviewer_ieee", "review"): "deep",
    ("reviewer_small", "review"): "standard",
    ("reviewer_blog", "review"): "simple",

    # Utility tasks (wildcard agent)
    ("any", "citation_formatting"): "simple",
    ("any", "metadata_extraction"): "simple",
    ("any", "bibtex_generation"): "simple",
}


class TaskClassifier:
    """Classifies tasks into complexity tiers for model routing."""

    def __init__(
        self, classification_map: dict[tuple[str, str], str] | None = None
    ) -> None:
        self.map = classification_map or TASK_CLASSIFICATION

    def classify(self, agent_type: str, task_phase: str) -> str:
        key = (agent_type, task_phase)
        if key in self.map:
            return self.map[key]
        wildcard_key = ("any", task_phase)
        if wildcard_key in self.map:
            return self.map[wildcard_key]
        return "standard"
