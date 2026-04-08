# mneme-hermes

Mneme-Hermes is a starting point for bringing Mneme-style memory quality, provenance, and git-aware maintenance workflows into Hermes.

## Why this exists

Hermes already has:
- built-in curated memory
- optional external memory providers
- searchable session history
- a wiki/knowledge-base workflow

Mneme brings a complementary philosophy:
- verify recall health
- recover durable facts from messy notes
- compile memory into more usable structures
- audit duplicates, contradictions, and stale memory
- keep provenance visible

Mneme-Hermes aims to connect those ideas cleanly to Hermes.

## Initial direction

This repo starts with two concrete tracks:

1. Git-aware wiki maintenance for Hermes-style research wikis
2. Mneme-inspired memory quality layer for Hermes memory and knowledge stores

## Near-term goals

### 1. Repo-aware wiki updater
Build a Hermes-friendly update workflow that:
- stores the last ingested git commit for a repo
- computes commit/file deltas
- groups changes by subsystem
- emits raw-source snapshots for the wiki
- updates only affected wiki pages
- avoids page-per-file and page-per-commit explosion

### 2. Memory quality layer
Explore a Hermes-compatible layer that can:
- inspect built-in memory health
- detect stale or conflicting facts
- recover durable facts from transcripts or notes
- compile memory into more reusable structures
- preserve provenance for every promoted fact

### 3. Future Hermes integration
Possible later forms:
- a skill + script workflow
- a Hermes plugin
- an external memory provider
- a hybrid of the above

## Initial repo structure

- `docs/vision.md` — what Mneme-Hermes is trying to become
- `docs/roadmap.md` — phased development plan
- `docs/hermes-fit.md` — mapping Mneme ideas onto Hermes architecture
- `docs/repo-wiki-updater.md` — spec for git-aware wiki maintenance
- `docs/memory-quality-layer.md` — spec for Hermes memory-quality workflows
- `examples/` — future example configs, prompts, and sample outputs
- `scripts/` — future implementation scripts

## Current status

This is day-zero scaffolding.

The main purpose today is to lock in direction and give the project a clean starting point.

## Credits

Started by Nova ✨ (Hermes)
