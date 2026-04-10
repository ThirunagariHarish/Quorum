# SPEC-010: Notification System

**Status:** Draft
**Priority:** P0
**Phase:** 2 (Week 4) for Telegram setup; Phase 5 (Week 11) for full integration
**Dependencies:** SPEC-006 (Token Engine for budget alerts), SPEC-001 (Orchestrator for topic notifications)

---

## 1. Overview

Quorum uses Telegram Bot API as the primary notification channel. The bot sends topic suggestions, review-ready alerts, budget warnings, and daily summaries. Users can respond to topic suggestions directly in Telegram using inline keyboard buttons.

## 2. Telegram Bot Setup

### 2.1 Bot Creation

1. User messages `@BotFather` in Telegram
2. Sends `/newbot` and chooses a name (e.g., "Quorum Bot")
3. Receives a bot token (format: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyz`)
4. User enters the token in Quorum Settings page

### 2.2 Chat ID Discovery

After the user sends any message to the bot, the backend discovers the chat ID:

```python
async def get_chat_id(bot_token: str) -> str:
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    response = await httpx.get(url)
    updates = response.json()["result"]
    if updates:
        return str(updates[0]["message"]["chat"]["id"])
    raise ValueError("No messages found. User must message the bot first.")
```

### 2.3 Configuration Storage

| Setting | Key | Encrypted |
|---------|-----|-----------|
| Bot token | `telegram_bot_token` | Yes (AES-256) |
| Chat ID | `telegram_chat_id` | No |

## 3. Notification Types

### 3.1 Topic Suggestions

Sent after each Research Orchestrator cycle.

```
📋 Quorum: New Topics Discovered

Morning research cycle found 5 trending topics:

1. Zero-Knowledge V2X Authentication
   Score: 8.7 | Suggested: IEEE Full Paper
   
2. Federated Learning for AV Swarm Intelligence  
   Score: 8.2 | Suggested: IEEE Full Paper

3. Smart Contract Incentives for Honest V2V Reporting
   Score: 7.9 | Suggested: Short Paper

4. Building a Blockchain-Based AV Trust System
   Score: 7.5 | Suggested: Blog Series

5. Cross-Chain Interoperability for Multi-Network AVs
   Score: 7.1 | Suggested: Short Paper

Select topics to research (you can pick multiple):
```

**Inline Keyboard:**
```
[1. ZK V2X Auth    ] [2. Fed Learning  ]
[3. Smart Contract ] [4. AV Trust Blog ]
[5. Cross-Chain    ]
[✅ Confirm Selection] [❌ Skip This Cycle]
```

### 3.2 Review-Ready Notification

Sent when papers complete generation and automated review.

```
📝 Quorum: Papers Ready for Review

3 papers are ready for your review:

1. "ZK-Proofs for V2X Authentication" (IEEE)
   Auto-review: 7/10 | Plagiarism: 8.5%
   
2. "Building AV Trust - Part 1" (Blog)
   Auto-review: 8/10 | Plagiarism: 4.2%

3. "Federated V2V Consensus" (Short Paper)
   Auto-review: 6/10 | Plagiarism: 11.3%

Review at: https://paperpilot.example.com/review
```

### 3.3 Budget Alerts

Sent when token budget crosses thresholds.

**WARNING (70%):**
```
⚠️ Quorum: Budget Warning

Daily budget: 70% consumed ($7.00 / $10.00)
Monthly: $189 / $300

Opus tasks will be downgraded to Sonnet.
Adjust budget: https://paperpilot.example.com/settings
```

**CRITICAL (90%):**
```
🔴 Quorum: Budget Critical

Daily budget: 92% consumed ($9.20 / $10.00)

All tasks downgraded to Haiku.
Remaining agents may produce lower quality output.
```

**EXHAUSTED (100%):**
```
🛑 Quorum: Budget Exhausted

Daily limit of $10.00 reached. All agents paused.

Options:
• Wait until tomorrow (resets at 00:00 UTC)
• Increase budget in Settings
```

### 3.4 Daily Summary

Sent at end of day (23:00 UTC).

```
📊 Quorum: Daily Summary (April 10, 2026)

Agent Activity:
• Research Orchestrator: 2 cycles, 8 topics discovered
• IEEE Agent: 2 papers generated
• Small Paper Agent: 1 paper generated
• Blog Agent: 1 series (3 parts) generated
• Review Agents: 4 reviews completed

Papers Status:
• 1 approved (ready for submission)
• 2 in review
• 1 revision requested

Token Usage:
• Total: $7.20 (72% of daily budget)
• Opus: $2.50 | Sonnet: $3.80 | Haiku: $0.90
• 3 model downgrades applied

Upcoming Deadlines:
• IEEE ICBC 2026: 96 days remaining (2 papers targeting)
```

### 3.5 Agent Error Notification

Sent when an agent encounters an unrecoverable error.

```
❌ Quorum: Agent Error

IEEE Research Agent encountered an error:
"LaTeX compilation failed after 3 retry attempts"

Task: "ZK-Proofs for V2X Authentication"
Phase: Paper Assembly

Action required: Check agent logs in dashboard.
```

## 4. Telegram API Integration

### 4.1 Send Message

```python
import httpx

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.chat_id = chat_id

    async def send_message(self, text: str, parse_mode: str = "HTML") -> dict:
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            return response.json()

    async def send_with_inline_keyboard(
        self, text: str, buttons: list[list[dict]]
    ) -> dict:
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": buttons
            },
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            return response.json()

    async def send_document(
        self, file_path: str, caption: str = ""
    ) -> dict:
        url = f"{self.base_url}/sendDocument"
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                response = await client.post(
                    url,
                    data={"chat_id": self.chat_id, "caption": caption},
                    files={"document": f},
                )
            return response.json()
```

### 4.2 Webhook for Callback Queries

When users click inline keyboard buttons, Telegram sends callback queries to a webhook:

```python
# backend/app/api/telegram.py
from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "callback_query" in data:
        callback = data["callback_query"]
        callback_data = callback["data"]  # e.g., "select_topic:1" or "confirm" or "skip"
        user_chat_id = str(callback["message"]["chat"]["id"])

        if callback_data == "confirm":
            await process_topic_selections(user_chat_id)
        elif callback_data == "skip":
            await skip_cycle(user_chat_id)
        elif callback_data.startswith("select_topic:"):
            topic_index = int(callback_data.split(":")[1])
            await toggle_topic_selection(user_chat_id, topic_index)

        # Acknowledge the callback
        await answer_callback_query(callback["id"])

    return {"ok": True}
```

### 4.3 Webhook Registration

On startup (or when Telegram settings are saved):

```python
async def register_webhook(bot_token: str, webhook_url: str):
    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    payload = {"url": webhook_url}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        return response.json()
```

## 5. Notification Preferences

Users can configure which notifications they receive in Settings:

| Setting Key | Default | Description |
|------------|---------|-------------|
| `notification_topic_suggestions` | true | Topic discovery results |
| `notification_review_ready` | true | Papers ready for review |
| `notification_budget_alerts` | true | Budget threshold warnings |
| `notification_daily_summary` | true | End-of-day summary |
| `notification_agent_errors` | true | Agent error alerts |
| `notification_deadline_reminders` | true | Upcoming deadline reminders |

## 6. Rate Limits

Telegram Bot API limits:
- 30 messages per second to different chats
- 1 message per second to the same chat
- 20 messages per minute to the same group

Since Quorum sends to a single user, the effective limit is ~1 message/second. Queue notifications if multiple arrive simultaneously.

## 7. Error Handling

| Error | Recovery |
|-------|---------|
| Telegram API timeout | Retry with exponential backoff (1s, 2s, 4s) up to 3 attempts |
| Invalid bot token | Log error; show "Telegram disconnected" in dashboard; disable notifications |
| Chat ID not found | Prompt user to message the bot first; retry on next notification |
| Webhook registration fails | Fall back to polling mode (getUpdates every 5s) |
| Message too long (>4096 chars) | Split into multiple messages |
