---
key: session_memory_recall
name: Session Memory Recall
one_line_summary: Recover prior conversation state from workspace artifacts, verify the latest usable session evidence, and compress it into reusable continuation memory.
description: Locate prior conversation artifacts in the project, verify the most recent usable session traces, extract only tool-verified facts, and summarize them into concise reusable memory for future task continuation. When raw session files are unavailable, fall back to bounded secondary evidence with explicit uncertainty.
category: memory
tags:
  - session
  - memory
  - recall
  - history
  - context
  - summarization
  - retrieval
form: sop
language: en
os:
  - windows
  - linux
  - macos
shell:
  - powershell
  - bash
runtimes:
  - python
tools:
  - file_read
  - code_run
needs_tool_calling: true
needs_reasoning: true
min_context_window: standard
decay_risk: medium
clarity: 4
completeness: 5
actionability: 5
autonomous_safe: true
blast_radius: low
requires_credentials: false
data_exposure: low
effect_scope: local
estimated_tokens: medium
capabilities:
  - locate prior session artifacts
  - verify recent conversation traces
  - distinguish primary from secondary evidence
  - extract actionable facts only
  - summarize conversation into reusable memory
---

# Session Memory Recall

## Purpose
Use this skill when the task depends on recovering what happened in a previous conversation round, especially when the active context is incomplete but the workspace may still contain logs, model responses, session dumps, or memory artifacts.

## When to use
- The user says “继续上一轮”、“回忆之前聊到哪了”、“搜索上一轮会话记录”
- The current context is clearly missing prior decisions or progress
- There are likely session traces in files, logs, or generated artifacts
- You need a verified summary rather than a guessed recollection

## Inputs
- User request related to prior conversation recovery
- Workspace path
- Existing memory hierarchy (`L1/L2/L3/L4`) if available
- Current injected working memory, if present

## Outputs
- A verified summary of the latest relevant prior session
- Key prior decisions, constraints, and pending next steps
- Evidence source classification: primary vs secondary
- If needed, a concise reusable memory note or SOP pointer

## Core rules
1. Only trust tool-verified artifacts.
2. Do not fabricate missing conversation content.
3. Prefer the most recent usable trace, but verify it is not just the current turn.
4. Extract facts, decisions, constraints, and next actions — not verbose chat filler.
5. If evidence is partial, explicitly mark it as partial.
6. Working memory is secondary evidence, not raw conversation evidence.
7. Do not store volatile identifiers like transient session IDs or timestamps into long-term memory unless the user explicitly asks for this specific run.

## Evidence priority
Probe in this order, and cross-check when possible:

1. `memory/L4_raw_sessions/`
   - If raw archived sessions exist, prefer them first.
2. Project logs and history-like artifacts
   - Examples: `model_responses`, `history`, `session`, `archive`, `transcript`, `chat`, `response`, `log`
   - Search recursively instead of guessing one filename.
3. Current injected working memory
   - Use as bounded secondary evidence when raw traces are missing.
4. Related memory SOPs or reports
   - Helpful as context, but not a substitute for raw session proof.

If `L4_raw_sessions/` has no usable data but project logs clearly contain the prior round, summarize from those logs.

## Retrieval strategy
### 1. Clarify target scope
Decide whether the user wants:
- the immediate previous round
- the latest relevant discussion
- prior decisions about a topic
- a general recap of earlier conversation

If unclear, default to the most recent verifiable prior round.

### 2. Check structured memory first
Look for:
- `global_mem_insight.txt`
- `global_mem.txt`
- relevant L3 SOP files
- `L4_raw_sessions/` or other history/session directories

Goal:
- Determine whether a prior summary already exists
- Avoid redundant full-project search if a reusable pointer is already present

### 3. Search the workspace for session-like artifacts
If structured memory is insufficient, search for:
- `session`
- `history`
- `conversation`
- `chat`
- `model_responses`
- `transcript`
- `response`
- task-specific logs or generated traces

Prefer:
- recent files
- append-only logs
- structured artifacts with timestamps or turn boundaries

### 4. Verify recency and relevance
Before summarizing, confirm:
- the file is from a prior round, not only the current turn
- the matched section actually contains user/assistant exchange content
- the extracted content is relevant to the user’s requested continuation

Common checks:
- if the current file only contains this turn, switch to an adjacent or earlier file
- read the tail and nearby context
- when boundaries are unclear, extract only the visible continuous fragment

### 5. Summarize into reusable memory
Compress into:
- user goal
- confirmed findings
- decisions already made
- constraints discovered
- unfinished next step
- evidence source
- uncertainty, if any

Keep the summary short, factual, and reusable across sessions.

## Recommended summary template
Use a compact structure like:

```md
### Prior Session Summary
- User goal:
- Confirmed facts:
- Agent actions completed:
- Current blocker / unfinished work:
- Evidence source:
- Uncertainty:
```

## Good extraction targets
Prioritize:
- confirmed file paths
- resolved blockers
- selected strategies
- rejected approaches with reason
- exact next action that was pending

## Avoid
Do not preserve:
- speculation
- unverified assumptions
- raw long dialogue unless necessary
- volatile runtime state
- irrelevant emotional or conversational filler

## Failure handling
- First failed search: inspect directory structure and alternative artifact names
- Second failed search: widen search scope and sort by modification time
- Third failed search: explicitly report that no verified raw prior session artifact was found, then provide the best bounded summary from currently available secondary evidence only

## Typical failure corrections
- Failure: conclude “no session exists” after checking only `L4_raw_sessions/`
  - Correction: continue recursive search across project logs and history artifacts
- Failure: treat working memory as raw conversation proof
  - Correction: label it as secondary evidence
- Failure: fill narrative gaps by guessing missing rounds
  - Correction: extract only visible fragments and mark unclear boundaries
- Failure: write one-off file numbers, timestamps, or transient IDs into long-term memory
  - Correction: preserve only stable retrieval methods and reusable conclusions

## Safe memory distillation rule
If writing the recovered result into memory:
- store only stable, reusable conclusions
- keep L1 as a minimal pointer only
- put task-specific reusable technique into L3 SOP if it has ongoing value
- never write guessed content into memory

## Example use cases
### Example 1
User asks:
> 继续搜索上一轮会话记录

Action:
- inspect memory
- scan project for session/history artifacts
- read recent matched files
- confirm latest prior usable trace
- summarize only verified conversation state

### Example 2
User asks:
> 你之前帮我定位到哪里了？

Action:
- locate prior trace
- extract the last confirmed milestone
- answer with a concise status summary and next step

## Success criteria
This skill is successful if it can:
- identify the most recent relevant prior session evidence
- reconstruct a trustworthy summary from files
- clearly separate primary evidence, secondary evidence, and unknowns
- provide a continuation-ready memory snapshot