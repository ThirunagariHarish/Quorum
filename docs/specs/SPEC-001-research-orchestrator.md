# SPEC-001: Research Orchestrator Agent

**Status:** Draft
**Priority:** P0
**Phase:** 2 (Weeks 3-4)
**Dependencies:** Token Budget Engine (SPEC-006), Search Integrations (SPEC-014), Notifications (SPEC-010)

---

## 1. Overview

The Research Orchestrator is the primary agent that runs on a twice-daily schedule. It discovers trending research topics across blockchain, autonomous vehicles, and AI, ranks them by novelty and relevance, presents selections to the user, and dispatches work to the specialized generation agents (IEEE, Small Paper, Blog).

## 2. Agent Configuration

```python
from claude_agent_sdk import AgentDefinition

ORCHESTRATOR_DEFINITION = AgentDefinition(
    description="Research orchestrator that discovers trending topics and delegates paper/blog generation tasks to specialized agents.",
    prompt=ORCHESTRATOR_SYSTEM_PROMPT,  # see Section 4
    tools=[
        "Read",
        "Write",
        "Bash",
        "WebSearch",
        "WebFetch",
        "Agent",           # to spawn sub-agents
    ],
    model="claude-sonnet-4-20250514",  # Sonnet for cost-efficient orchestration
)
```

### Model Assignment

| Task Phase | Model | Rationale |
|-----------|-------|-----------|
| Topic discovery and search | Sonnet | Multi-source synthesis, moderate reasoning |
| Topic ranking and scoring | Sonnet | Structured decision-making |
| Task delegation | Sonnet | Routing logic, not deep reasoning |
| Status summaries | Haiku (via Token Engine downgrade) | Simple data aggregation |

## 3. Schedule

| Parameter | Default | Configurable |
|-----------|---------|-------------|
| Morning run | 06:00 UTC | Yes, via Settings |
| Evening run | 18:00 UTC | Yes, via Settings |
| Scheduler | APScheduler CronTrigger | Backend service |
| Max runtime per cycle | 30 minutes | Yes |

### Trigger Flow

```
APScheduler CronTrigger fires
    |
    v
backend/app/services/scheduler.py calls agents/orchestrator/agent.py
    |
    v
Orchestrator agent starts with Claude Agent SDK query()
    |
    v
Agent uses search tools to discover topics
    |
    v
Agent ranks topics and formats selection message
    |
    v
System sends Telegram notification with inline keyboard
    |
    v
User responds -> Telegram webhook -> backend creates AgentTask records
    |
    v
Orchestrator dispatches to IEEE/SmallPaper/Blog agents
```

## 4. System Prompt

The Orchestrator's system prompt must embed the following instructions:

```
You are the Research Orchestrator for Quorum. Your job is to discover trending 
research topics and delegate paper generation tasks to specialized agents.

NICHE AREAS (loaded from user settings):
{niche_topics}

SCHEDULE: You run twice daily. Each run follows this protocol:

PHASE 1 - DISCOVERY
1. Query the following APIs for papers published in the last 48 hours:
   - OpenAlex: search by niche topic keywords, sort by citation count
   - arXiv: query cs.CR (cryptography), cs.RO (robotics), cs.AI (AI) categories
   - Semantic Scholar: search with relevance ranking
   - IEEE Xplore: search within blockchain, autonomous vehicles, AI conferences
2. For each discovered paper, extract: title, abstract, authors, venue, date, DOI, citation count
3. Deduplicate across sources by DOI or title similarity (>85% Jaccard)

PHASE 2 - RANKING
Score each topic on three dimensions (1-10 scale):
- Novelty: How recent and underexplored is this area? Prefer papers < 30 days old with < 10 citations.
- Extension potential: Can this paper be extended with new methodology, different datasets, or cross-domain application?
- Niche fit: How well does this align with the user's configured niche topics?

Final score = (Novelty * 0.4) + (Extension * 0.35) + (Niche fit * 0.25)

PHASE 3 - SELECTION
1. Select top 5 topics by score
2. For each topic, suggest a content type:
   - IEEE Full Paper: if the topic has deep extension potential and a target conference deadline is within 8 weeks
   - Short Paper: if the topic is narrowly scoped or a workshop deadline is near
   - Blog Article: if the topic is implementation-oriented or trending on social media
3. Format as a numbered list with: title, one-sentence summary, suggested type, score

PHASE 4 - DELEGATION
After user selects topics (received via task assignment):
1. For each selected IEEE paper topic: invoke the ieee-researcher agent with the topic, reference papers, and target venue
2. For each selected short paper topic: invoke the small-paper agent with the topic and reference papers
3. For each selected blog topic: invoke the blog-writer agent with the topic and implementation angle

CONSTRAINTS:
- Never fabricate paper titles, authors, or DOIs during discovery
- If no trending topics are found, report this honestly rather than inventing topics
- Respect API rate limits: max 10 requests per API per cycle
- Total runtime must not exceed 30 minutes per cycle
```

## 5. Topic Ranking Algorithm

### Input
List of discovered papers from all four search APIs (deduplicated).

### Scoring Dimensions

**Novelty Score (0-10):**
- Published < 7 days ago: +4 points
- Published 7-30 days ago: +2 points
- Published 30-90 days ago: +1 point
- Citation count < 5: +3 points (underexplored)
- Citation count 5-20: +2 points
- First paper in a new sub-topic: +3 points

**Extension Potential (0-10):**
- Methodology can be applied to different domain: +3 points
- Results show clear limitations acknowledged by authors: +3 points
- Small dataset used (opportunity for larger-scale validation): +2 points
- No existing follow-up papers found: +2 points

**Niche Fit (0-10):**
- Exact match with user's configured topic keywords: +5 points
- Intersection of two niche areas (e.g., blockchain + AV): +5 points
- Single niche area match: +3 points
- Adjacent topic (e.g., IoT security for AV): +1 point

### Output
Ranked list of topics with scores, sorted by final score descending.

## 6. Task Assignment Protocol

When the user selects topics via Telegram, the Orchestrator creates `AgentTask` records:

```json
{
  "agent_type": "ieee",
  "topic": "Zero-Knowledge Proofs for Autonomous Vehicle V2X Authentication",
  "reference_papers": [
    {"doi": "10.1109/...", "title": "...", "source": "ieee_xplore"}
  ],
  "content_type": "ieee_full",
  "target_venue": "IEEE ICBC 2026",
  "target_deadline": "2026-07-15",
  "priority": 1,
  "status": "queued"
}
```

## 7. Knowledge Graph (P1 - Future)

The Orchestrator maintains a lightweight knowledge graph to avoid re-researching topics:

- **Nodes**: Topics, Papers, Authors, Venues
- **Edges**: "extends", "cites", "authored_by", "published_at"
- **Storage**: PostgreSQL JSONB column on a `knowledge_graph` table
- **Usage**: Before ranking, check if a topic has already been assigned to an agent; penalize score by -5 if so

## 8. Error Handling

| Error | Recovery |
|-------|---------|
| Search API timeout | Retry once after 30s; skip API if still failing; proceed with remaining APIs |
| No topics found | Send Telegram message: "No trending topics discovered in this cycle" |
| User doesn't respond to Telegram within 4 hours | Auto-select top 3 topics with highest scores |
| Agent SDK call fails | Log error; retry once; if still failing, mark task as failed and notify user |
| Token budget exhausted mid-cycle | Complete current phase; pause before delegation; notify user |

## 9. Metrics

| Metric | Tracked In |
|--------|-----------|
| Topics discovered per cycle | `agent_tasks` table |
| Topics selected by user (acceptance rate) | `agent_tasks` table |
| API response times per source | Application logs |
| Token usage per cycle | `token_usage_logs` table |
| Cycle duration (wall clock) | Application logs |
