# Quorum -- Product Requirements Document

**Version:** 1.0
**Date:** April 10, 2026
**Author:** Harish Kumar
**Status:** Draft

---

## 1. Product Vision

Quorum is an autonomous multi-agent research and publishing platform that continuously discovers trending topics, generates high-quality academic papers and implementation-focused blog articles, orchestrates peer-review simulations, and manages the full lifecycle from ideation to publication -- all powered by a team of specialized Claude AI agents operating 24/7.

### 1.1 Problem Statement

Academic researchers face three compounding bottlenecks:

1. **Discovery overhead** -- Staying current across blockchain, autonomous vehicles, and AI requires monitoring dozens of journals, preprint servers, and news sources daily.
2. **Production throughput** -- Writing a single IEEE-quality paper takes weeks of literature review, experimentation, and LaTeX formatting.
3. **Publication friction** -- Tracking submission deadlines, formatting requirements, and reviewer feedback across multiple venues is error-prone and time-consuming.

Quorum eliminates these bottlenecks by deploying a coordinated swarm of AI agents that operate like a personal research lab -- discovering, writing, reviewing, and publishing on the researcher's behalf.

### 1.2 Target Niche

- Blockchain technology (consensus, DeFi, smart contracts, tokenomics)
- Autonomous vehicle systems (perception, planning, V2X communication)
- AI/ML systems (LLMs, reinforcement learning, federated learning)
- **Intersections**: Blockchain + AV (trustless V2V, reward systems, decentralized coordination), AI + Blockchain (on-chain ML, verifiable inference), AI + AV (end-to-end driving, anomaly detection)

### 1.3 Success Metrics

| Metric | Target | Timeframe |
|--------|--------|-----------|
| Papers generated per week | 5-10 drafts | Month 2+ |
| Papers passing human review | 60%+ | Month 3+ |
| IEEE submissions per quarter | 3-5 | Quarter 2+ |
| Blog articles published per week | 2-3 | Month 2+ |
| Token cost per paper | < $15 average | Ongoing |
| Daily operational cost | < $10/day | Ongoing |

---

## 2. User Personas

### 2.1 Primary: Solo Researcher (Harish)

- **Role:** Graduate researcher / independent publisher
- **Goals:** Publish consistently across IEEE conferences and technical blogs; build academic authority in blockchain + AV + AI
- **Pain points:** Limited time for literature reviews; manual LaTeX formatting; missing submission deadlines; inconsistent publishing cadence
- **Technical comfort:** High -- comfortable with APIs, cloud infrastructure, and code

### 2.2 Secondary: Academic Collaborator

- **Role:** Co-author or advisor reviewing drafts
- **Goals:** Review and provide feedback on generated papers before submission
- **Pain points:** Receiving unformatted drafts; lack of centralized review interface
- **Technical comfort:** Moderate -- can use a web dashboard but should not need CLI access

---

## 3. Core Workflows

### 3.1 Twice-Daily Research Cycle

```
06:00 / 18:00 UTC
    |
    v
Research Orchestrator wakes up
    |
    v
Scans OpenAlex, arXiv, IEEE Xplore, Semantic Scholar
    |
    v
Ranks discovered topics by novelty, citation potential, niche fit
    |
    v
Sends top 3-5 topics to user via Telegram
    |
    v
User selects 1-3 topics + content type (IEEE / Short Paper / Blog)
    |
    v
Orchestrator assigns tasks to appropriate agents
    |
    v
Agents begin multi-hour research and generation
    |
    v
Output files stored in MinIO, metadata in PostgreSQL
    |
    v
Review agents validate output
    |
    v
User notified: "Papers ready for review"
```

### 3.2 Paper Generation Workflow

```
Task assigned by Orchestrator
    |
    v
Agent receives topic + reference papers + content type
    |
    v
Phase 1: Literature survey (Sonnet)
  - Search APIs for related work
  - Extract key findings, gaps, methodologies
    |
    v
Phase 2: Ideation (Opus)
  - Generate 5-6 extension ideas from the base paper
  - Each idea becomes a sub-agent task
    |
    v
Phase 3: Sub-agent swarm (Haiku for scouts, Sonnet for writers)
  - Each sub-agent researches one extension direction
  - Generates methodology, experiments, results
    |
    v
Phase 4: Paper assembly (Sonnet)
  - Compile sections into IEEE LaTeX format
  - Generate citations, figures, tables
    |
    v
Phase 5: Self-review (Opus)
  - Check novelty, consistency, formatting
  - Flag issues for human review
    |
    v
Output: LaTeX source + compiled PDF
```

### 3.3 Human Review Workflow

```
User opens Review Center
    |
    v
Left panel: list of papers pending review
    |
    v
Click paper -> Center panel: PDF/LaTeX preview
    |
    v
Right panel: add inline comments/notes
    |
    v
Option A: "Send Feedback" -> Paper returns to agent queue
    |                         Agent incorporates feedback
    |                         Resubmits for review
    |
    v
Option B: "Approve" -> Paper moves to "Approved" tab
                        Available for download/submission
```

### 3.4 Blog Publishing Workflow

```
Blog Agent completes Part 1/2/3 series
    |
    v
Review Agent validates code, tone, accuracy
    |
    v
User reviews in Review Center
    |
    v
User clicks "Publish to dev.to"
    |
    v
System publishes via dev.to API (as draft or live)
    |
    v
Optional: User imports to Medium via canonical URL
```

---

## 4. Functional Requirements

### FR-1: Research Orchestrator Agent

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | Run automatically at configurable intervals (default: 06:00 and 18:00 UTC) | P0 |
| FR-1.2 | Query OpenAlex, arXiv, IEEE Xplore, and Semantic Scholar APIs for trending papers | P0 |
| FR-1.3 | Rank discovered topics by novelty score, citation potential, and niche relevance | P0 |
| FR-1.4 | Send top 3-5 ranked topics to user via Telegram with selectable options | P0 |
| FR-1.5 | Accept user's topic selection and content type assignment | P0 |
| FR-1.6 | Dispatch tasks to IEEE Agent, Small Paper Agent, or Blog Agent based on selection | P0 |
| FR-1.7 | Track all active agent tasks and report status to dashboard | P0 |
| FR-1.8 | Check upcoming conference/journal deadlines and factor into topic suggestions | P1 |
| FR-1.9 | Maintain a knowledge graph of previously researched topics to avoid duplication | P1 |
| FR-1.10 | Use Sonnet model for all orchestration tasks (cost-efficient decision-making) | P0 |

### FR-2: IEEE Research Agent

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | Accept a topic + reference paper(s) and generate a full IEEE-format research paper | P0 |
| FR-2.2 | Output in LaTeX using official IEEE conference/journal templates | P0 |
| FR-2.3 | Generate proper IEEE-style citations with BibTeX | P0 |
| FR-2.4 | Spawn 5-6 sub-agents to explore different extension directions from the base paper | P0 |
| FR-2.5 | Each sub-agent produces a complete paper with Abstract, Introduction, Related Work, Methodology, Results, Conclusion | P0 |
| FR-2.6 | Verify all citations reference real, existing papers (no hallucinated references) | P0 |
| FR-2.7 | Ensure novel contribution -- not just restating existing work | P0 |
| FR-2.8 | Support both 8-page full papers and 4-page short papers | P1 |
| FR-2.9 | Include experiment design with reproducible methodology | P1 |
| FR-2.10 | Use Opus for methodology creation and ideation; Sonnet for structure and compilation | P0 |

### FR-3: Small Paper Agent

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | Generate 2-4 page workshop/poster papers in IEEE LaTeX format | P0 |
| FR-3.2 | Faster turnaround than full IEEE papers (target: 2-3 hours per paper) | P0 |
| FR-3.3 | Focus on concise contribution statements with preliminary results | P0 |
| FR-3.4 | Support SoK (Systemisation of Knowledge) format up to 16 pages | P2 |
| FR-3.5 | Use Sonnet model for all generation tasks | P0 |

### FR-4: Blog Implementation Agent

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | Generate implementation-focused blog articles, not just explanations | P0 |
| FR-4.2 | Structure articles as multi-part series: Part 1 (Problem + Architecture), Part 2 (Implementation + Code), Part 3 (Results + Improvements) | P0 |
| FR-4.3 | Include working code examples that a reader could follow along with | P0 |
| FR-4.4 | Write in a natural, human tone -- avoid detectable AI writing patterns | P0 |
| FR-4.5 | Generate architecture diagrams and code screenshots | P1 |
| FR-4.6 | Output in Markdown format compatible with dev.to API | P0 |
| FR-4.7 | Include proper code blocks with syntax highlighting markers | P0 |
| FR-4.8 | Use Sonnet for writing, Haiku for code scaffolding | P0 |

### FR-5: Review Agents

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-5.1 | One review agent per content type: IEEE, Small Paper, Blog | P0 |
| FR-5.2 | Check for plagiarism via Copyleaks API; reject if similarity > 15% | P0 |
| FR-5.3 | Validate IEEE formatting compliance (margins, fonts, section structure, citation format) | P0 |
| FR-5.4 | Assess novelty: reject if the paper merely restates existing work | P0 |
| FR-5.5 | Check logical consistency between methodology and results | P0 |
| FR-5.6 | Verify all citations are real papers with valid DOIs/URLs | P0 |
| FR-5.7 | Generate structured review feedback with severity levels (blocker, major, minor, suggestion) | P0 |
| FR-5.8 | Send rejected papers back to the generating agent with specific feedback | P0 |
| FR-5.9 | Limit review-rework cycles to 3 iterations before flagging for human review | P1 |
| FR-5.10 | IEEE Review Agent uses Opus; Small Paper uses Sonnet; Blog uses Haiku | P0 |

### FR-6: Dashboard

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-6.1 | **Home page**: Show recent outputs, active agent status, pending notifications | P0 |
| FR-6.2 | **Agents panel**: Per-agent view with Files tab, Current Tasks tab, History tab, Performance metrics | P0 |
| FR-6.3 | **Files explorer**: List all generated documents with preview, download, and approval status filters | P0 |
| FR-6.4 | **Review Center**: 3-panel layout -- file list (left), document viewer (center), comments/notes (right) | P0 |
| FR-6.5 | LaTeX/PDF document viewer using PDF.js | P0 |
| FR-6.6 | Inline comment system with "Add Note" button for review feedback | P0 |
| FR-6.7 | "Send Feedback" button returns paper to agent with comments attached | P0 |
| FR-6.8 | "Approve" button moves paper to approved files section | P0 |
| FR-6.9 | **Settings panel**: Anthropic API key, Telegram bot config, dev.to API key, niche topics list, notification preferences | P0 |
| FR-6.10 | **Token usage dashboard**: Per-agent cost breakdown, daily/monthly trends, budget remaining, model distribution charts | P0 |
| FR-6.11 | Real-time agent status updates via WebSocket | P1 |
| FR-6.12 | Dark mode support | P1 |
| FR-6.13 | Responsive design for tablet/mobile viewing | P2 |
| FR-6.14 | Manual task assignment: user can give an agent a specific task from the Agents panel | P1 |

### FR-7: Token Budget & Model Routing System

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-7.1 | Track token usage per agent, per session, per task, and in daily/monthly aggregates | P0 |
| FR-7.2 | Classify tasks into complexity tiers: simple (Haiku), standard (Sonnet), deep-reasoning (Opus) | P0 |
| FR-7.3 | Route each agent call to the appropriate model based on task classification | P0 |
| FR-7.4 | Allow user to set daily and monthly token budget limits in Settings | P0 |
| FR-7.5 | Alert user at 70% and 90% budget consumption via Telegram and dashboard | P0 |
| FR-7.6 | Auto-downgrade model tier when budget is constrained: Opus -> Sonnet at 70% spent, all -> Haiku at 90% spent | P0 |
| FR-7.7 | Pause all agents when budget is exhausted; notify user immediately | P0 |
| FR-7.8 | Log all token usage with timestamps to PostgreSQL for historical analysis | P0 |
| FR-7.9 | Display cost forecasting on dashboard based on current usage trends | P1 |
| FR-7.10 | Support prompt caching to reduce costs (90% discount on cache hits) | P1 |

### FR-8: Notification System

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-8.1 | Send topic suggestions to user via Telegram with inline keyboard for selection | P0 |
| FR-8.2 | Notify user when papers are ready for review | P0 |
| FR-8.3 | Send budget alerts at threshold levels | P0 |
| FR-8.4 | Send daily summary of agent activity and outputs | P1 |
| FR-8.5 | Support sending PDF documents via Telegram for quick review | P1 |
| FR-8.6 | Allow user to respond to topic suggestions directly in Telegram | P0 |

### FR-9: Publishing Pipeline

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-9.1 | Publish blog articles to dev.to via REST API | P0 |
| FR-9.2 | Support multi-part series with automatic linking | P0 |
| FR-9.3 | Publish as draft or live based on user preference | P0 |
| FR-9.4 | Support cover image upload for articles | P1 |
| FR-9.5 | Set canonical URL for cross-posting to Medium | P1 |
| FR-9.6 | One-click "Publish" button in dashboard for approved blog articles | P0 |
| FR-9.7 | Track published articles with links back to dev.to | P0 |

### FR-10: Submission Deadline Tracker

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-10.1 | Maintain a database of relevant IEEE conferences and journals with submission deadlines | P1 |
| FR-10.2 | Display upcoming deadlines on the dashboard with countdown timers | P1 |
| FR-10.3 | Associate generated papers with target venues | P1 |
| FR-10.4 | Recommend suitable journals/conferences based on paper topic and quality | P2 |
| FR-10.5 | Alert user 2 weeks and 1 week before submission deadlines | P1 |

---

## 5. Non-Functional Requirements

| ID | Category | Requirement | Target |
|----|----------|-------------|--------|
| NFR-1 | Availability | Agents must operate 24/7 with automatic restart on failure | 99.5% uptime |
| NFR-2 | Performance | Dashboard page load time | < 2 seconds |
| NFR-3 | Performance | Agent response to task assignment | < 30 seconds to begin |
| NFR-4 | Security | API keys encrypted at rest using AES-256 | Mandatory |
| NFR-5 | Security | Dashboard authentication via JWT with configurable expiry | Mandatory |
| NFR-6 | Security | No credentials stored in plaintext or version control | Mandatory |
| NFR-7 | Cost | Token spend must not exceed user-configured budget | Mandatory |
| NFR-8 | Cost | Estimated monthly cost with optimized model routing | $150-300 |
| NFR-9 | Scalability | Support running up to 20 concurrent sub-agents | Phase 6 |
| NFR-10 | Data | All generated files backed up to S3-compatible storage | Mandatory |
| NFR-11 | Observability | Structured logging for all agent actions with correlation IDs | P1 |
| NFR-12 | Compliance | Generated papers must have < 15% plagiarism similarity score | Mandatory |

---

## 6. Constraints and Risks

### 6.1 Technical Constraints

| Constraint | Impact | Mitigation |
|-----------|--------|------------|
| Medium API is closed to new integrations (since March 2023) | Cannot publish directly to Medium | Use dev.to API with canonical URL import to Medium |
| Claude context window is 200K tokens (Haiku) / 1M tokens (Sonnet/Opus beta) | Long papers may exceed context | Chunk processing; use sessions for context persistence |
| IEEE Xplore API requires developer registration during business hours | Delayed access to IEEE paper search | Use OpenAlex and arXiv as primary; IEEE Xplore as supplementary |
| LaTeX compilation requires a TeX engine | Dependency management | Use Tectonic (self-contained, auto-downloads packages) |

### 6.2 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| AI-generated content detected by IEEE reviewers | Medium | High | Human editing layer; diverse writing styles; real experiment data |
| LLM hallucination produces fake citations | High | Critical | Citation verification agent checks every reference against real databases |
| Plagiarism detection flags generated content | Medium | High | Copyleaks pre-check; iterative rewriting on high similarity |
| Token costs exceed budget | Medium | Medium | Token Budget Engine with auto-downgrade and hard budget caps |
| Agent enters infinite review-rework loop | Low | Medium | Cap review iterations at 3; escalate to human |
| IEEE conference deadlines missed | Medium | Medium | Deadline tracker with 2-week advance notifications |
| Rate limiting from search APIs | Low | Low | Request throttling; caching; multiple API fallbacks |

---

## 7. Out of Scope (v1)

- WhatsApp Business API integration (requires Meta business verification)
- Gmail integration for document delivery (Telegram covers notifications)
- AI detection evasion tooling (ethical boundary -- human editing is the correct mitigation)
- Automated IEEE submission (human must submit manually)
- Multi-user/multi-tenant support
- Mobile native application

---

## 8. Glossary

| Term | Definition |
|------|-----------|
| **Research Orchestrator** | Primary agent that discovers topics and delegates to specialized agents |
| **Sub-agent swarm** | Group of 5-6 agents spawned to explore different research directions for a single topic |
| **Review loop** | Cycle where a review agent rejects a paper, sends feedback, and the generating agent revises |
| **Token Budget Engine** | System component that tracks API token usage and routes tasks to cost-appropriate models |
| **Model routing** | Dynamic selection of Claude model (Haiku/Sonnet/Opus) based on task complexity and budget |
| **dev.to** | Technical blogging platform with working REST API; replacement for Medium's closed API |
| **Tectonic** | Self-contained LaTeX engine used for compiling .tex files to PDF |
| **OpenAlex** | Free academic database with 250M+ works; primary paper discovery source |

---

## 9. Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | Harish Kumar | | |
| Technical Lead | | | |
| Reviewer | | | |
