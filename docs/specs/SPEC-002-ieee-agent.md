# SPEC-002: IEEE Research Agent

**Status:** Draft
**Priority:** P0
**Phase:** 3 (Weeks 5-7)
**Dependencies:** SPEC-001 (Orchestrator), SPEC-006 (Token Engine), SPEC-012 (LaTeX Pipeline), SPEC-014 (Search APIs)

---

## 1. Overview

The IEEE Research Agent generates full conference and journal papers in IEEE LaTeX format. For each assigned topic, it spawns 5-6 sub-agents to explore different research extension directions, then assembles the best output into a complete paper. It is the most token-intensive agent and uses Opus for deep research tasks and Sonnet for structural work.

## 2. Agent Configuration

```python
IEEE_AGENT = AgentDefinition(
    description="IEEE conference/journal paper researcher and writer. Generates full LaTeX papers with citations, methodology, and experimental results.",
    prompt=IEEE_SYSTEM_PROMPT,
    tools=[
        "Read", "Write", "Bash",
        "WebSearch", "WebFetch",
        "Agent",  # spawns sub-agents for parallel research directions
    ],
    model="claude-opus-4-20250514",
)
```

### Model Assignment by Task Phase

| Phase | Model | Est. Tokens | Rationale |
|-------|-------|-------------|-----------|
| Literature survey | Sonnet | ~50K | Multi-paper synthesis, not deep reasoning |
| Ideation (5-6 directions) | Opus | ~30K | Creative research thinking |
| Sub-agent scouting | Haiku | ~10K each | Quick feasibility assessment |
| Sub-agent full research | Sonnet | ~40K each | Extended writing and analysis |
| Paper assembly | Sonnet | ~30K | Compilation and formatting |
| Self-review | Opus | ~20K | Critical evaluation |
| **Total per paper** | **Mixed** | **~250-350K** | |

## 3. IEEE Paper Format Rules

### 3.1 Structure

Every generated paper must contain these sections in order:

1. **Title** -- Concise, descriptive, no abbreviations
2. **Abstract** -- 150-250 words summarizing problem, method, results, contribution
3. **Index Terms** -- 4-6 IEEE taxonomy keywords
4. **Introduction** -- Problem statement, motivation, contribution summary, paper organization
5. **Related Work** -- Survey of 10-20 relevant papers with proper citations
6. **Methodology / Proposed Approach** -- Detailed technical description
7. **Experimental Setup** -- Datasets, baselines, metrics, environment
8. **Results and Discussion** -- Tables, figures, statistical analysis
9. **Conclusion** -- Summary, limitations, future work
10. **References** -- IEEE-style bibliography (minimum 15 references)

### 3.2 Formatting Rules

| Rule | Specification |
|------|--------------|
| Template | IEEE Conference 2-column format |
| Page limit | 8 pages (excluding references) for full papers |
| Font | Times New Roman, minimum 10pt |
| Margins | IEEE standard (top: 0.75in, bottom: 1in, left/right: 0.625in) |
| Columns | 2-column layout, 0.25in gap |
| Figures | Centered, captioned below, referenced in text |
| Tables | Captioned above, referenced in text |
| Equations | Numbered sequentially, right-aligned |
| Citations | IEEE numeric style: [1], [2], [3] |
| References | IEEE format with DOIs where available |

### 3.3 LaTeX Template

```latex
\documentclass[conference]{IEEEtran}
\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{algorithmic}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{booktabs}

\begin{document}

\title{Paper Title Here}

\author{
  \IEEEauthorblockN{Author Name}
  \IEEEauthorblockA{
    \textit{Department, University} \\
    City, Country \\
    email@domain.com
  }
}

\maketitle

\begin{abstract}
% 150-250 words
\end{abstract}

\begin{IEEEkeywords}
keyword1, keyword2, keyword3, keyword4
\end{IEEEkeywords}

\section{Introduction}
% ...

\section{Related Work}
% ...

\section{Proposed Approach}
% ...

\section{Experimental Setup}
% ...

\section{Results and Discussion}
% ...

\section{Conclusion}
% ...

\bibliographystyle{IEEEtran}
\bibliography{references}

\end{document}
```

## 4. Sub-Agent Swarm Protocol

When the IEEE Agent receives a topic with reference papers, it follows this process:

### 4.1 Ideation Phase (Opus)

The agent analyzes the reference paper and generates 5-6 extension directions:

```
Given reference paper: "Blockchain-Based V2V Trust Management"

Extension directions:
1. Replace trust metric with zero-knowledge proofs for privacy
2. Apply to V2I (vehicle-to-infrastructure) instead of V2V
3. Use federated learning instead of centralized trust aggregation
4. Benchmark with larger-scale SUMO simulation (10K vehicles)
5. Add smart contract-based incentive mechanism for honest reporting
6. Cross-chain interoperability for multi-network AV ecosystems
```

### 4.2 Scout Phase (Haiku Sub-Agents)

For each direction, spawn a Haiku sub-agent to assess feasibility:

```python
SCOUT_AGENT = AgentDefinition(
    description="Quick feasibility scout for a research direction.",
    prompt="Assess whether this research direction is feasible...",
    tools=["WebSearch", "WebFetch"],
    model="claude-haiku-4-20250514",
)
```

Each scout returns:
- Feasibility score (1-10)
- Key references found
- Potential challenges
- Estimated novelty (has this been done before?)

### 4.3 Research Phase (Sonnet Sub-Agents)

Top 3-4 directions (by feasibility score) get full Sonnet sub-agents:

```python
RESEARCH_AGENT = AgentDefinition(
    description="Full research agent for one extension direction.",
    prompt="Research and write a complete IEEE paper section...",
    tools=["Read", "Write", "WebSearch", "WebFetch", "Bash"],
    model="claude-sonnet-4-20250514",
)
```

Each research sub-agent:
1. Conducts thorough literature search for the specific direction
2. Designs methodology with pseudocode and algorithm descriptions
3. Designs experiments with specific datasets, metrics, and baselines
4. Generates synthetic/simulated results (clearly marked as simulated if no real execution)
5. Writes the complete paper in LaTeX

### 4.4 Assembly Phase (Sonnet)

The IEEE Agent selects the best sub-agent output and:
1. Reviews all sub-agent papers for quality
2. Selects the strongest paper or combines sections from multiple
3. Ensures citation consistency and formatting compliance
4. Compiles the final LaTeX document
5. Stores in MinIO and creates `Paper` record

## 5. Citation Rules

### 5.1 Requirements

- Minimum 15 references per full paper
- Every claim must be backed by a citation or marked as "our contribution"
- At least 30% of citations must be from the last 3 years
- IEEE-style numeric citation format: [1], [2-4], [5]

### 5.2 Verification

Before finalizing any paper, the citation verification tool:

1. Extracts all BibTeX entries
2. For each entry, queries OpenAlex or Semantic Scholar by DOI or title
3. Verifies: paper exists, authors match, venue matches, year matches
4. Flags unverifiable citations with severity "blocker"
5. Reports verification rate (target: 100% real citations)

### 5.3 BibTeX Format

```bibtex
@inproceedings{smith2025blockchain,
  author    = {J. Smith and A. Johnson},
  title     = {Blockchain-Based Trust Management for Autonomous Vehicles},
  booktitle = {IEEE International Conference on Blockchain and Cryptocurrency (ICBC)},
  year      = {2025},
  pages     = {1--8},
  doi       = {10.1109/ICBC51069.2025.00001},
}
```

## 6. Novelty Extension Strategy

The agent must ensure each paper represents a genuine extension, not a restatement:

| Extension Type | Description | Example |
|---------------|-------------|---------|
| Methodology swap | Replace a core technique with an alternative | Replace PBFT with HotStuff consensus |
| Domain transfer | Apply the approach to a different domain | V2V trust -> drone swarm trust |
| Scale validation | Test at significantly larger scale | 100 vehicles -> 10,000 vehicles |
| Component addition | Add a new system component | Add privacy layer via ZK-proofs |
| Hybrid approach | Combine two existing approaches | Blockchain + federated learning |
| Ablation study | Systematically remove/modify components | Test with/without incentive mechanism |

## 7. Output Specification

Each completed paper produces:

| File | Format | Storage |
|------|--------|---------|
| `paper.tex` | LaTeX source | MinIO: `papers/{paper_id}/paper.tex` |
| `references.bib` | BibTeX bibliography | MinIO: `papers/{paper_id}/references.bib` |
| `paper.pdf` | Compiled PDF | MinIO: `papers/{paper_id}/paper.pdf` |
| `figures/*.png` | Generated figures | MinIO: `papers/{paper_id}/figures/` |
| `metadata.json` | Paper metadata (title, abstract, keywords, citations) | PostgreSQL `papers` table |

## 8. Target Conferences and Journals

The agent should be aware of these relevant venues:

| Venue | Type | Typical Deadline | Page Limit |
|-------|------|-----------------|------------|
| IEEE ICBC | Conference | Varies (check annually) | 8 pages |
| IEEE IV (Intelligent Vehicles) | Conference | ~January | 8 pages |
| IEEE ITSC (Intelligent Transportation) | Conference | ~March | 6 pages |
| IEEE Blockchain | Conference | ~June | 8 pages |
| IEEE T-ITS (Trans. Intelligent Transport.) | Journal | Rolling | 12 pages |
| IEEE T-IFS (Trans. Info. Forensics & Sec.) | Journal | Rolling | 14 pages |
| IEEE Access | Journal | Rolling | 20 pages |

## 9. Error Handling

| Error | Recovery |
|-------|---------|
| Sub-agent produces plagiarized content (>15% similarity) | Discard output; spawn replacement sub-agent with explicit originality instructions |
| Citation verification fails for >3 references | Return to research phase; agent must find real citations |
| LaTeX compilation fails | Log error; attempt auto-fix of common LaTeX errors; escalate to human if still failing |
| Sub-agent exceeds token budget | Terminate sub-agent; use its partial output if useful |
| All sub-agent outputs are low quality | Flag for human review; do not auto-publish |
