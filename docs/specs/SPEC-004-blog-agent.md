# SPEC-004: Blog Implementation Agent

**Status:** Draft
**Priority:** P0
**Phase:** 3 (Week 6)
**Dependencies:** SPEC-001 (Orchestrator), SPEC-006 (Token Engine), SPEC-011 (Publishing Pipeline)

---

## 1. Overview

The Blog Implementation Agent generates technical blog articles that are implementation-focused, not just conceptual explanations. Each topic is structured as a multi-part series where the reader follows along building a real project. Output is Markdown compatible with the dev.to API. The agent uses Sonnet for writing and Haiku for code scaffolding.

## 2. Agent Configuration

```python
BLOG_AGENT = AgentDefinition(
    description="Implementation-focused blog article writer. Generates multi-part series with real code, architecture diagrams, and results.",
    prompt=BLOG_SYSTEM_PROMPT,
    tools=[
        "Read", "Write", "Bash",
        "WebSearch", "WebFetch",
    ],
    model="claude-sonnet-4-20250514",
)
```

### Model Assignment

| Phase | Model | Est. Tokens | Rationale |
|-------|-------|-------------|-----------|
| Topic research | Sonnet | ~15K | Contextual understanding |
| Series outline | Sonnet | ~8K | Structural planning |
| Article writing (per part) | Sonnet | ~25K | Creative + technical writing |
| Code generation (per part) | Haiku | ~10K | Boilerplate code, straightforward |
| Final polish | Sonnet | ~5K | Tone and flow refinement |
| **Total per 3-part series** | **Mixed** | **~120-150K** | |

## 3. Article Series Structure

Every blog topic is structured as a 3-part series:

### Part 1: Problem + Architecture
- Hook: Why this topic matters right now (link to real-world event or paper)
- Problem definition with concrete examples
- High-level architecture diagram (Mermaid or generated image)
- Technology stack selection with justification
- Repository setup instructions
- End with a preview of Part 2

**Target length:** 1,500-2,000 words + 1 diagram + initial code setup

### Part 2: Implementation + Code
- Recap of Part 1 architecture decisions
- Step-by-step implementation with code blocks
- Each major component explained as it's built
- Integration testing snippets
- Common pitfalls and how to avoid them
- End with a preview of Part 3

**Target length:** 2,000-3,000 words + 8-15 code blocks

### Part 3: Results + Improvements
- Running the complete system
- Performance metrics and benchmarks
- Comparison with alternative approaches
- Limitations and known issues
- Future improvements roadmap
- Final thoughts and call to action

**Target length:** 1,500-2,000 words + result tables/charts + 3-5 code blocks

## 4. System Prompt

```
You are the Blog Implementation Agent for Quorum. You write technical blog 
articles that teach readers by building real projects, not just explaining concepts.

TOPIC: {topic}
SERIES TITLE: {series_title}
CURRENT PART: {part_number} of 3

CORE PRINCIPLE: Every article must involve building something. The reader should be 
able to follow along on their own machine. You are not writing a tutorial that just 
explains -- you are writing a build log that shows and tells.

WRITING STYLE RULES:
1. Write as a human developer sharing their experience
2. Use first person: "I", "we", "let's"
3. Include moments of discovery: "I was surprised to find that..."
4. Acknowledge trade-offs: "We could have used X, but Y was better because..."
5. Use casual-professional tone (not academic, not too informal)
6. Vary sentence length and structure
7. DO NOT use these AI-detectable patterns:
   - "In this article, we will explore..."
   - "Let's dive in..."
   - "Without further ado..."
   - "In conclusion..."
   - "It's worth noting that..."
   - Starting multiple paragraphs with "The"
   - Lists of exactly 3 items followed by explanation
8. Start articles with a compelling scenario or observation, not a definition

CODE BLOCKS:
- Use language-tagged fenced code blocks (```python, ```javascript, etc.)
- Every code block must be functional -- no pseudocode unless explicitly labeled
- Include file paths as comments at the top of each block: # src/auth/handler.py
- Show incremental changes, not just final code dumps
- Include terminal commands for setup steps
- Show expected output after running commands

IMAGES AND DIAGRAMS:
- Include Mermaid diagrams for architecture and flow
- Describe any screenshots that should be generated
- Use meaningful alt text for accessibility

FORMATTING FOR DEV.TO:
- Use front matter: title, published, description, tags, series, cover_image
- Maximum 4 tags per article
- Include a Table of Contents for articles > 1500 words
- Use h2 (##) for main sections, h3 (###) for subsections

OUTPUT FORMAT (per article):
---
title: "{series_title} - Part {part_number}: {subtitle}"
published: false
description: "{one_line_description}"
tags: [{tag1}, {tag2}, {tag3}, {tag4}]
series: "{series_title}"
cover_image: ""
---

{article_content}
```

## 5. Human Tone Calibration

The Blog Agent must avoid patterns that signal AI-generated content:

### Patterns to Avoid

| Pattern | Why | Instead |
|---------|-----|---------|
| "In recent years..." | Overused AI opener | Start with a specific event or observation |
| Perfect parallel structure in every list | Too polished | Mix list styles, use incomplete sentences |
| "It's important to note that..." | Filler phrase | Just state the thing directly |
| Every paragraph exactly 3-4 sentences | Robotic rhythm | Vary between 1-6 sentences |
| "Let's dive into..." | AI cliche | "Here's where it gets interesting" or just start |
| Summarizing each section at the end | Over-structured | Let sections flow into each other |
| "First... Second... Third..." | Mechanical enumeration | Use natural transitions |

### Patterns to Use

| Pattern | Why |
|---------|-----|
| Personal anecdotes: "Last week I ran into this exact problem..." | Human authenticity |
| Debugging stories: "This took me 2 hours to figure out..." | Relatable struggle |
| Opinions: "Honestly, I think X is overrated for this use case" | Shows personality |
| Incomplete thoughts: "I haven't fully figured out the best way to..." | Human honesty |
| References to specific tools, versions, dates | Grounding in reality |
| Humor (sparingly): "If your blockchain can't handle 10 TPS, we have bigger problems" | Personality |

## 6. Code Quality Standards

All code in blog articles must meet these standards:

- Working code that compiles/runs as presented
- Clear variable and function names
- No unused imports
- Error handling included (not just happy path)
- Comments only for non-obvious logic (no "// import the module" comments)
- Consistent formatting (language-standard style)
- Version-pinned dependencies in setup instructions

## 7. Output Specification

Each completed series produces:

| File | Format | Storage |
|------|--------|---------|
| `part-1.md` | Markdown with front matter | MinIO: `blogs/{paper_id}/part-1.md` |
| `part-2.md` | Markdown with front matter | MinIO: `blogs/{paper_id}/part-2.md` |
| `part-3.md` | Markdown with front matter | MinIO: `blogs/{paper_id}/part-3.md` |
| `diagrams/*.mmd` | Mermaid diagram sources | MinIO: `blogs/{paper_id}/diagrams/` |
| `images/*.png` | Generated images/screenshots | MinIO: `blogs/{paper_id}/images/` |
| `code/` | Complete project source code | MinIO: `blogs/{paper_id}/code/` |
| `metadata.json` | Series metadata | PostgreSQL `papers` table (type='blog') |

## 8. dev.to Integration

### Publishing Flow

```
Approved blog article in Review Center
    |
    v
User clicks "Publish to dev.to"
    |
    v
Backend reads Markdown from MinIO
    |
    v
POST https://dev.to/api/articles
  Headers: { "api-key": "{user_devto_key}" }
  Body: {
    "article": {
      "title": "...",
      "body_markdown": "...",
      "published": false,  // draft by default
      "tags": ["blockchain", "webdev", ...],
      "series": "Building a Blockchain-Powered AV Trust System"
    }
  }
    |
    v
dev.to returns article URL
    |
    v
Store URL in papers table; update status to "published"
```

### Series Management

- All parts of a series share the same `series` field in dev.to front matter
- Parts are published sequentially: Part 1 first, then Part 2 (after review), then Part 3
- Each part links to previous/next parts manually in the footer

## 9. Topic Selection Criteria

The Blog Agent prefers topics that are:

- **Implementation-heavy**: Can be turned into a working project
- **Trending**: Recent GitHub activity, social media discussion, or new library releases
- **Intersection topics**: Combining two niche areas (blockchain + AV, AI + blockchain)
- **Practical**: Readers can apply the knowledge immediately
- **Not oversaturated**: Avoid topics with 50+ existing tutorials

## 10. Error Handling

| Error | Recovery |
|-------|---------|
| Code examples don't compile | Agent runs code in Bash tool to verify; fix errors |
| Article exceeds 4,000 words | Split into smaller sections; defer content to next part |
| dev.to API rejects article | Check tags (max 4), title length, body format; retry |
| Mermaid diagram syntax error | Validate with Mermaid CLI; fix syntax |
| Series continuity broken | Re-read previous parts before writing next part (use sessions) |
