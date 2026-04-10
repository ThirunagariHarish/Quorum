# SPEC-003: Small Paper Agent

**Status:** Draft
**Priority:** P0
**Phase:** 3 (Week 6)
**Dependencies:** SPEC-001 (Orchestrator), SPEC-006 (Token Engine), SPEC-012 (LaTeX Pipeline)

---

## 1. Overview

The Small Paper Agent generates short workshop papers (2-4 pages) and poster papers (2 pages) in IEEE LaTeX format. It is designed for faster turnaround than the full IEEE Agent, targeting workshop and poster sessions at conferences. It uses the Sonnet model exclusively for a balance of quality and cost.

## 2. Agent Configuration

```python
SMALL_PAPER_AGENT = AgentDefinition(
    description="Short workshop and poster paper writer. Generates 2-4 page IEEE-format papers with concise contributions.",
    prompt=SMALL_PAPER_SYSTEM_PROMPT,
    tools=[
        "Read", "Write",
        "WebSearch", "WebFetch",
    ],
    model="claude-sonnet-4-20250514",
)
```

### Model Assignment

| Phase | Model | Est. Tokens | Rationale |
|-------|-------|-------------|-----------|
| Quick literature scan | Sonnet | ~15K | Focused search, fewer papers |
| Paper writing | Sonnet | ~30K | Concise writing |
| Self-check | Sonnet | ~10K | Basic validation |
| **Total per paper** | **Sonnet** | **~55K** | |

### Turnaround Target

- **2-page poster paper:** 1-2 hours
- **4-page workshop paper:** 2-3 hours

## 3. Paper Format Rules

### 3.1 Structure (4-page Workshop Paper)

1. **Title** -- Concise and specific
2. **Abstract** -- 100-150 words
3. **Introduction** -- Problem + motivation + contribution (1 column)
4. **Approach** -- Key technique description (1-1.5 columns)
5. **Preliminary Results** -- Key findings with 1-2 figures/tables
6. **Conclusion and Future Work** -- Brief summary + next steps
7. **References** -- 8-15 references

### 3.2 Structure (2-page Poster Paper)

1. **Title**
2. **Abstract** -- 80-100 words
3. **Introduction and Motivation** -- 0.5 column
4. **Proposed Approach** -- 0.5-1 column
5. **Expected Contributions** -- 0.5 column
6. **References** -- 5-10 references

### 3.3 Formatting

| Rule | Specification |
|------|--------------|
| Template | IEEE Conference 2-column format |
| Page limit | 4 pages (workshop) or 2 pages (poster), excluding references |
| Font | Times New Roman, minimum 10pt |
| Columns | 2-column layout |
| Citations | IEEE numeric style |

### 3.4 LaTeX Template

Uses the same `IEEEtran` document class as full papers with `\documentclass[conference]{IEEEtran}`. The only difference is the reduced page count enforced by prompt instructions.

## 4. System Prompt

```
You are the Small Paper Agent for Quorum. You write short workshop and poster 
papers in IEEE LaTeX format.

PAPER TYPE: {paper_type}  (workshop_4page | poster_2page)
TOPIC: {topic}
REFERENCE PAPERS: {reference_papers}

INSTRUCTIONS:

For WORKSHOP (4-page) papers:
1. Conduct a focused literature search: find 8-15 directly relevant papers
2. Identify ONE clear, narrow contribution
3. Write with emphasis on the approach and preliminary results
4. Use 1-2 figures or tables to illustrate key findings
5. Keep the writing dense and precise -- every sentence must earn its place
6. Conclusion must clearly state limitations and planned future work

For POSTER (2-page) papers:
1. Find 5-10 directly relevant papers
2. Focus on the proposed idea and expected contributions
3. Results can be preliminary or expected (clearly labeled)
4. Prioritize clarity and visual appeal for poster presentation

WRITING STYLE:
- Academic tone, third person
- No filler phrases ("In recent years...", "It is well known that...")
- Each paragraph should start with a clear topic sentence
- Quantify claims wherever possible

CITATION RULES:
- Every factual claim needs a citation
- Prefer citing papers from the last 3 years
- All citations must reference real, verifiable papers
- Use IEEE numeric citation style [1], [2]

OUTPUT:
- main.tex (LaTeX source)
- references.bib (BibTeX file)
- Any figure files referenced
```

## 5. Generation Pipeline

```
Topic + references received from Orchestrator
    |
    v
Quick literature scan (5-10 minutes)
  - Search OpenAlex + arXiv for directly relevant work
  - Extract 8-15 key references
    |
    v
Outline generation
  - Draft section headings with 1-2 sentence descriptions
  - Identify the single core contribution
    |
    v
Full paper writing
  - Write all sections sequentially
  - Generate BibTeX entries for all citations
    |
    v
Self-check
  - Verify page count within limits
  - Verify all citations have corresponding BibTeX entries
  - Check for common LaTeX errors
    |
    v
Output: .tex + .bib + figures -> MinIO
```

## 6. Differentiation from IEEE Agent

| Aspect | IEEE Agent (SPEC-002) | Small Paper Agent |
|--------|----------------------|-------------------|
| Page count | 8 pages | 2-4 pages |
| Sub-agent swarm | Yes (5-6 agents) | No (single agent) |
| Model | Opus + Sonnet | Sonnet only |
| Research depth | Deep, multi-directional | Focused, single-direction |
| Turnaround | 6-12 hours | 1-3 hours |
| Token cost | ~250-350K tokens | ~55K tokens |
| Results | Full experimental results | Preliminary/expected results |
| Target venues | Main conferences/journals | Workshops, posters, symposia |

## 7. Output Specification

| File | Format | Storage |
|------|--------|---------|
| `main.tex` | LaTeX source | MinIO: `papers/{paper_id}/main.tex` |
| `references.bib` | BibTeX bibliography | MinIO: `papers/{paper_id}/references.bib` |
| `paper.pdf` | Compiled PDF | MinIO: `papers/{paper_id}/paper.pdf` |
| `figures/*.png` | Generated figures (if any) | MinIO: `papers/{paper_id}/figures/` |

## 8. Quality Checklist

Before marking a paper as complete, the agent self-validates:

- [ ] Page count within limit (2 or 4 pages, excluding references)
- [ ] Abstract within word limit
- [ ] At least one clear contribution statement in Introduction
- [ ] All figures/tables referenced in text
- [ ] All citations have valid BibTeX entries
- [ ] No placeholder text remaining
- [ ] LaTeX compiles without errors
- [ ] References count within range (5-15)

## 9. Error Handling

| Error | Recovery |
|-------|---------|
| Paper exceeds page limit | Trim Results or Related Work sections; tighten prose |
| Too few references found | Broaden search terms; include adjacent topics |
| LaTeX compilation failure | Auto-fix common errors (missing braces, undefined references); retry |
| Token budget insufficient for Sonnet | Downgrade literature scan to Haiku; keep writing in Sonnet |
