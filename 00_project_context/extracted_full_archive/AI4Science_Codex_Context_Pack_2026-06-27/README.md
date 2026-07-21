# AI4Science / XRD Reliability — Codex Context Pack

**Version:** 2026-06-27  
**Language:** Chinese-first, English technical terminology retained  
**Purpose:** Give Codex a durable, repository-local source of truth for the user's AI4Science research work.

## What this pack is

This is a **curated project context pack**, not an unfiltered raw-chat dump. It contains:

- the current authoritative research direction;
- experimental and physical constraints;
- decisions already made and decisions deliberately left open;
- a 12-week MVP plan;
- legacy FerroAI audit context that motivated the current reliability agenda;
- task prompts that can be pasted into Codex;
- a catalog and an optional local copy of the project reference PDFs.

## What this pack is not

- It is **not** a claim that every historical brainstorming idea remains active.
- It does **not** contain inaccessible platform-side raw chat logs.
- It does **not** settle unresolved physical numerical ranges, dataset licenses, or real-XRD protocols.

## Codex read order

1. `AGENTS.md` — non-negotiable implementation rules.
2. `context/00_CURRENT_STATE.md` — current authoritative snapshot.
3. `context/02_SIMXRD_XRD_RELIABILITY_SPEC.md` — task and method specification.
4. `context/03_EXPERIMENT_PROTOCOL.md` + `context/04_PHYSICAL_VALIDITY.md` — experiment design and physics boundaries.
5. Task-relevant files in `context/` and the matching prompt in `prompts/`.
6. Read `legacy/` only when historical motivation or FerroAI comparisons are relevant.

## How to install

Copy this folder into the **repository root** of the codebase that Codex will operate on. Keep `AGENTS.md` at that root. Do not merge its content blindly with another project: first reconcile any conflicting build/test instructions.

## Authority hierarchy

```text
AGENTS.md
  > context/00_CURRENT_STATE.md
  > context/06_DECISION_LOG.md
  > context/10_KNOWN_UNCERTAINTIES.md
  > task-specific files
  > legacy history
```

When two files disagree, newer `Decision Log` entries and the `Current State` take precedence. When a conflict remains, stop and ask the user rather than guessing.

## Suggested first Codex task

Open `prompts/00_BOOTSTRAP_FOR_CODEX.md`, paste it as the first message, then request the initial data/schema audit. Do **not** begin model implementation until the dataset fields, label mapping, split mechanism, and license/usage constraints are visible in the repository.
