# SPEC-009: API Contracts

**Status:** Draft
**Priority:** P0
**Phase:** 1-5 (progressive)
**Dependencies:** SPEC-008 (Data Model)

---

## 1. Overview

Quorum exposes a REST API for CRUD operations and a WebSocket API for real-time updates. Both are served by a FastAPI backend.

## 2. Base Configuration

| Property | Value |
|----------|-------|
| Base URL | `/api/v1` |
| Auth | JWT Bearer token (except login endpoint) |
| Content-Type | `application/json` |
| Error format | `{ "detail": "message", "code": "ERROR_CODE" }` |
| Pagination | `?page=1&per_page=20` (default 20, max 100) |
| Sorting | `?sort_by=created_at&sort_order=desc` |

## 3. Authentication Endpoints

### POST /api/v1/auth/login

Login and receive JWT token.

**Request:**
```json
{
  "email": "harish@example.com",
  "password": "secure_password"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**Errors:** `401 INVALID_CREDENTIALS`, `429 RATE_LIMITED`

### POST /api/v1/auth/refresh

Refresh an expired access token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOi..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOi...",
  "expires_in": 86400
}
```

### GET /api/v1/auth/me

Get current user info.

**Response (200):**
```json
{
  "id": "uuid",
  "email": "harish@example.com",
  "display_name": "Harish Kumar",
  "created_at": "2026-04-10T00:00:00Z"
}
```

### POST /api/v1/auth/setup

First-time setup (creates user account). Only works when no users exist.

**Request:**
```json
{
  "email": "harish@example.com",
  "password": "secure_password",
  "display_name": "Harish Kumar"
}
```

## 4. Papers Endpoints

### GET /api/v1/papers

List all papers with filtering.

**Query Parameters:**
- `status` -- filter by status (draft, in_review, approved, published, rejected)
- `paper_type` -- filter by type (ieee_full, ieee_short, workshop, poster, blog)
- `agent_id` -- filter by generating agent
- `page`, `per_page`, `sort_by`, `sort_order`

**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Zero-Knowledge Proofs for V2X Authentication",
      "abstract": "This paper presents...",
      "paper_type": "ieee_full",
      "status": "in_review",
      "current_version": 2,
      "keywords": ["blockchain", "V2X", "zero-knowledge"],
      "target_venue": "IEEE ICBC 2026",
      "plagiarism_score": 8.5,
      "review_cycles": 1,
      "agent_name": "IEEE Research Agent",
      "created_at": "2026-04-10T06:30:00Z",
      "updated_at": "2026-04-10T14:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

### GET /api/v1/papers/:id

Get paper details including version history.

**Response (200):**
```json
{
  "id": "uuid",
  "title": "...",
  "abstract": "...",
  "paper_type": "ieee_full",
  "status": "in_review",
  "current_version": 2,
  "keywords": ["blockchain", "V2X"],
  "target_venue": "IEEE ICBC 2026",
  "plagiarism_score": 8.5,
  "review_cycles": 1,
  "storage_prefix": "papers/uuid/",
  "pdf_url": "https://minio.../papers/uuid/paper.pdf?presigned=...",
  "versions": [
    { "version": 1, "created_at": "...", "change_summary": "Initial draft" },
    { "version": 2, "created_at": "...", "change_summary": "Addressed reviewer feedback on citations" }
  ],
  "reviews": [
    { "id": "uuid", "verdict": "revise", "quality": 6, "created_at": "..." }
  ],
  "agent_name": "IEEE Research Agent",
  "created_at": "2026-04-10T06:30:00Z"
}
```

### GET /api/v1/papers/:id/download

Get a presigned download URL for the paper file (PDF or LaTeX).

**Query Parameters:**
- `format` -- `pdf` (default) or `latex`
- `version` -- version number (default: latest)

**Response (200):**
```json
{
  "download_url": "https://minio.../papers/uuid/paper.pdf?X-Amz-...",
  "filename": "zk-v2x-authentication.pdf",
  "expires_in": 3600
}
```

### DELETE /api/v1/papers/:id

Delete a paper and all its versions.

**Response (204):** No content.

## 5. Agents Endpoints

### GET /api/v1/agents

List all agents with current status.

**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "IEEE Research Agent",
      "agent_type": "ieee",
      "default_model": "claude-opus-4-20250514",
      "status": "active",
      "current_task": {
        "id": "uuid",
        "topic": "ZK-Proofs for V2X",
        "phase": "ideation"
      },
      "total_tokens_used": 1250000,
      "total_cost_usd": 12.50,
      "last_active_at": "2026-04-10T14:30:00Z"
    }
  ]
}
```

### GET /api/v1/agents/:id

Get agent details with task history.

### GET /api/v1/agents/:id/tasks

List tasks for a specific agent.

**Query Parameters:** `status`, `page`, `per_page`

### POST /api/v1/agents/:id/tasks

Manually assign a task to an agent.

**Request:**
```json
{
  "topic": "Federated Learning for AV Swarm Intelligence",
  "content_type": "ieee_full",
  "target_venue": "IEEE IV 2027",
  "reference_papers": [
    { "doi": "10.1109/...", "title": "..." }
  ],
  "priority": 1
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "agent_id": "uuid",
  "topic": "...",
  "status": "queued",
  "created_at": "..."
}
```

## 6. Tasks Endpoints

### GET /api/v1/tasks

List all tasks across agents.

**Query Parameters:** `agent_id`, `status`, `content_type`, `page`, `per_page`

### GET /api/v1/tasks/:id

Get task details.

### PATCH /api/v1/tasks/:id

Update task (cancel, change priority).

**Request:**
```json
{
  "status": "cancelled"
}
```

## 7. Reviews Endpoints

### GET /api/v1/reviews

List reviews with filters.

**Query Parameters:** `paper_id`, `verdict`, `is_human_review`, `page`, `per_page`

### POST /api/v1/reviews

Create a human review with verdict.

**Request:**
```json
{
  "paper_id": "uuid",
  "verdict": "revise",
  "summary": "Good structure but citations need work.",
  "overall_quality": 7
}
```

### GET /api/v1/reviews/:id

Get review details including all comments.

### PATCH /api/v1/reviews/:id

Update review verdict (e.g., approve after revision).

### POST /api/v1/reviews/:id/comments

Add a comment to a review.

**Request:**
```json
{
  "content": "Section 3 methodology needs more detail on the experimental setup.",
  "severity": "major",
  "category": "logic",
  "location": "Section III, paragraph 2"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "review_id": "uuid",
  "content": "...",
  "severity": "major",
  "user_id": "uuid",
  "created_at": "..."
}
```

### POST /api/v1/reviews/:id/submit-feedback

Submit all comments as feedback and trigger agent rework.

**Response (200):**
```json
{
  "task_id": "uuid",
  "message": "Feedback sent. Agent will begin revision.",
  "revision_number": 2
}
```

### POST /api/v1/reviews/:id/approve

Approve a paper.

**Response (200):**
```json
{
  "paper_id": "uuid",
  "status": "approved",
  "message": "Paper approved and moved to approved files."
}
```

## 8. Files Endpoints

### GET /api/v1/files/:paperId/preview

Get a presigned URL for in-browser preview.

**Response (200):**
```json
{
  "preview_url": "https://minio.../papers/uuid/paper.pdf?presigned=...",
  "content_type": "application/pdf",
  "filename": "paper.pdf"
}
```

### GET /api/v1/files/:paperId/list

List all files for a paper.

**Response (200):**
```json
{
  "files": [
    { "key": "paper.tex", "size": 45000, "modified": "..." },
    { "key": "references.bib", "size": 3200, "modified": "..." },
    { "key": "paper.pdf", "size": 890000, "modified": "..." },
    { "key": "figures/arch.png", "size": 120000, "modified": "..." }
  ]
}
```

## 9. Publishing Endpoints

### POST /api/v1/publish/devto

Publish a blog article to dev.to.

**Request:**
```json
{
  "paper_id": "uuid",
  "part_number": 1,
  "published": false,
  "tags": ["blockchain", "webdev", "tutorial", "python"]
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "platform": "devto",
  "platform_article_id": "1234567",
  "published_url": "https://dev.to/harish/building-blockchain-av-trust-part-1-abc123",
  "status": "draft"
}
```

### GET /api/v1/publish/status/:id

Check publication status.

## 10. Token Usage Endpoints

### GET /api/v1/tokens/usage

Get token usage data with filters.

**Query Parameters:**
- `agent_id` -- filter by agent
- `model` -- filter by model
- `start_date`, `end_date` -- date range
- `granularity` -- `hourly`, `daily` (default), `monthly`

**Response (200):**
```json
{
  "data": [
    {
      "date": "2026-04-10",
      "total_cost_usd": 7.20,
      "total_input_tokens": 850000,
      "total_output_tokens": 195000,
      "api_calls": 45,
      "downgrades": 3
    }
  ],
  "summary": {
    "period_cost": 7.20,
    "daily_budget": 10.00,
    "daily_remaining": 2.80,
    "monthly_cost": 189.50,
    "monthly_budget": 300.00,
    "monthly_remaining": 110.50
  }
}
```

### GET /api/v1/tokens/budget

Get current budget configuration and status.

**Response (200):**
```json
{
  "daily_limit_usd": 10.00,
  "monthly_limit_usd": 300.00,
  "daily_spent": 7.20,
  "monthly_spent": 189.50,
  "budget_status": "warning",
  "auto_downgrade_enabled": true,
  "pause_on_exhaustion": true
}
```

### PUT /api/v1/tokens/budget

Update budget configuration.

**Request:**
```json
{
  "daily_limit_usd": 15.00,
  "monthly_limit_usd": 400.00,
  "auto_downgrade_enabled": true
}
```

### GET /api/v1/tokens/forecast

Get 30-day cost forecast.

**Response (200):**
```json
{
  "forecast_30d_usd": 245.00,
  "daily_average_7d": 8.15,
  "trend": "increasing",
  "projected_monthly": 252.65
}
```

## 11. Deadlines Endpoints

### GET /api/v1/deadlines

List all deadlines.

**Query Parameters:** `is_active`, `sort_by`

### POST /api/v1/deadlines

Create a new deadline.

**Request:**
```json
{
  "venue_name": "IEEE ICBC 2026",
  "venue_type": "conference",
  "submission_deadline": "2026-07-15T23:59:00Z",
  "venue_url": "https://icbc2026.ieee-icbc.org",
  "topics": ["blockchain", "cryptocurrency"],
  "page_limit": 8,
  "format_notes": "IEEE 2-column, double-blind review"
}
```

### DELETE /api/v1/deadlines/:id

Remove a deadline.

## 12. Settings Endpoints

### GET /api/v1/settings

Get all settings (sensitive values masked).

**Response (200):**
```json
{
  "anthropic_api_key": "sk-ant-...****",
  "anthropic_api_key_set": true,
  "telegram_bot_token_set": true,
  "telegram_chat_id": "123456789",
  "devto_api_key_set": true,
  "niche_topics": ["blockchain", "autonomous vehicles", "AI"],
  "custom_keywords": ["V2V", "ZK-proofs", "federated learning"],
  "daily_budget_usd": 10.00,
  "monthly_budget_usd": 300.00,
  "auto_downgrade": true,
  "schedule_morning": "06:00",
  "schedule_evening": "18:00"
}
```

### PUT /api/v1/settings

Update settings.

**Request:**
```json
{
  "anthropic_api_key": "sk-ant-api03-...",
  "niche_topics": ["blockchain", "autonomous vehicles", "AI", "IoT"],
  "daily_budget_usd": 15.00
}
```

## 13. Scheduler Endpoints

### POST /api/v1/scheduler/trigger

Manually trigger the research orchestrator.

**Response (200):**
```json
{
  "message": "Research Orchestrator triggered.",
  "task_id": "uuid"
}
```

### GET /api/v1/scheduler/status

Get scheduler status and next run times.

**Response (200):**
```json
{
  "is_running": true,
  "next_morning_run": "2026-04-11T06:00:00Z",
  "next_evening_run": "2026-04-10T18:00:00Z",
  "last_run": "2026-04-10T06:00:00Z",
  "last_run_status": "completed"
}
```

## 14. WebSocket API

### Connection

```
ws://host/ws?token={jwt_token}
```

### Server-to-Client Events

```typescript
interface WSEvent {
  type: string;
  payload: any;
  timestamp: string;
}

// Agent status change
{ type: "agent.status", payload: { agent_id: "uuid", status: "active", current_task: "..." } }

// Task progress
{ type: "task.progress", payload: { task_id: "uuid", agent_id: "uuid", phase: "writing", percent: 65 } }

// New paper generated
{ type: "paper.created", payload: { paper_id: "uuid", title: "...", type: "ieee_full" } }

// Review completed
{ type: "review.completed", payload: { review_id: "uuid", paper_id: "uuid", verdict: "approve" } }

// Token usage update
{ type: "token.usage", payload: { agent_id: "uuid", model: "sonnet", tokens: 5000, cost: 0.015 } }

// Budget alert
{ type: "budget.alert", payload: { level: "warning", remaining_pct: 28, message: "..." } }

// General notification
{ type: "notification", payload: { title: "Papers ready", message: "3 papers ready for review", action_url: "/review" } }
```

## 15. Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_CREDENTIALS` | 401 | Wrong email or password |
| `TOKEN_EXPIRED` | 401 | JWT token has expired |
| `UNAUTHORIZED` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Request body validation failed |
| `RATE_LIMITED` | 429 | Too many requests |
| `BUDGET_EXHAUSTED` | 402 | Token budget is exhausted |
| `AGENT_BUSY` | 409 | Agent is already processing a task |
| `PUBLISH_FAILED` | 502 | External publishing API error |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
