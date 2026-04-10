"""Telegram Bot notification service for Quorum."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends notifications to a user via Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.chat_id = chat_id

    # ------------------------------------------------------------------
    # Core methods
    # ------------------------------------------------------------------

    async def send_message(
        self, text: str, parse_mode: str = "HTML"
    ) -> dict[str, Any]:
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=15)
            return response.json()

    async def send_with_inline_keyboard(
        self, text: str, buttons: list[list[dict[str, str]]]
    ) -> dict[str, Any]:
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": buttons},
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=15)
            return response.json()

    async def send_document(
        self, file_bytes: bytes, filename: str, caption: str = ""
    ) -> dict[str, Any]:
        url = f"{self.base_url}/sendDocument"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                data={"chat_id": self.chat_id, "caption": caption},
                files={"document": (filename, file_bytes)},
                timeout=30,
            )
            return response.json()

    # ------------------------------------------------------------------
    # Message templates
    # ------------------------------------------------------------------

    @staticmethod
    def format_topic_suggestions(topics: list[dict[str, Any]]) -> tuple[str, list[list[dict[str, str]]]]:
        """Build message text and inline keyboard for topic suggestions.

        Returns ``(message_text, keyboard_buttons)``.
        """
        lines = ["<b>📋 Quorum: New Topics Discovered</b>\n"]
        buttons: list[list[dict[str, str]]] = []
        row: list[dict[str, str]] = []

        for idx, topic in enumerate(topics, 1):
            score = topic.get("score", 0)
            suggested = topic.get("suggested_type", "Paper")
            title = topic.get("title", "Untitled")
            lines.append(f"{idx}. <b>{title}</b>")
            lines.append(f"   Score: {score:.1f} | Suggested: {suggested}\n")
            row.append({"text": f"{idx}. {title[:20]}", "callback_data": f"select_topic:{idx}"})
            if len(row) == 2:
                buttons.append(row)
                row = []

        if row:
            buttons.append(row)

        buttons.append([
            {"text": "✅ Confirm Selection", "callback_data": "confirm"},
            {"text": "❌ Skip This Cycle", "callback_data": "skip"},
        ])

        return "\n".join(lines), buttons

    @staticmethod
    def format_review_ready(papers: list[dict[str, Any]], dashboard_url: str = "") -> str:
        lines = ["<b>📝 Quorum: Papers Ready for Review</b>\n"]
        for idx, paper in enumerate(papers, 1):
            title = paper.get("title", "Untitled")
            ptype = paper.get("paper_type", "")
            quality = paper.get("overall_quality", "?")
            plag = paper.get("plagiarism_score", "?")
            lines.append(f'{idx}. "<i>{title}</i>" ({ptype})')
            lines.append(f"   Auto-review: {quality}/10 | Plagiarism: {plag}%\n")
        if dashboard_url:
            lines.append(f"Review at: {dashboard_url}")
        return "\n".join(lines)

    @staticmethod
    def format_budget_alert(
        level: str,
        daily_spent: float,
        daily_limit: float,
        monthly_spent: float | None = None,
        monthly_limit: float | None = None,
    ) -> str:
        icons = {"warning": "⚠️", "critical": "🔴", "exhausted": "🛑"}
        icon = icons.get(level, "ℹ️")

        lines = [f"<b>{icon} Quorum: Budget {level.title()}</b>\n"]
        pct = (daily_spent / daily_limit * 100) if daily_limit else 0
        lines.append(f"Daily budget: {pct:.0f}% consumed (${daily_spent:.2f} / ${daily_limit:.2f})")

        if monthly_spent is not None and monthly_limit:
            lines.append(f"Monthly: ${monthly_spent:.0f} / ${monthly_limit:.0f}")

        if level == "exhausted":
            lines.append("\nAll agents have been paused.")
            lines.append("• Wait until tomorrow (resets at 00:00 UTC)")
            lines.append("• Increase budget in Settings")
        elif level == "critical":
            lines.append("\nAll tasks downgraded to Haiku.")
        elif level == "warning":
            lines.append("\nOpus tasks will be downgraded to Sonnet.")

        return "\n".join(lines)

    @staticmethod
    def format_daily_summary(
        agent_stats: dict[str, Any],
        paper_stats: dict[str, Any],
        token_stats: dict[str, Any],
    ) -> str:
        today_str = date.today().strftime("%B %d, %Y")
        lines = [f"<b>📊 Quorum: Daily Summary ({today_str})</b>\n"]

        lines.append("<b>Agent Activity:</b>")
        for agent_name, details in agent_stats.items():
            lines.append(f"• {agent_name}: {details}")

        lines.append("\n<b>Papers Status:</b>")
        for status, count in paper_stats.items():
            lines.append(f"• {count} {status}")

        lines.append("\n<b>Token Usage:</b>")
        for key, val in token_stats.items():
            lines.append(f"• {key}: {val}")

        return "\n".join(lines)
