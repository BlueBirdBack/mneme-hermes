# Roadmap

## Phase 0 — Usable local scaffold
- create repo
- define vision
- define specs for first two tracks
- add stdlib-only `mneme-hermes` CLI
- add `audit` report for Hermes memory files
- add `snapshot` backup command before manual edits
- add unittest coverage and agent quickstart docs

## Phase 1 — Repo-aware wiki updater
- define repo state file format
- record last-ingested commit
- compute git deltas
- map changed files to affected wiki pages
- emit raw markdown update snapshots

## Phase 2 — Memory quality checks
- inspect Hermes built-in memory files
- inspect session-derived evidence
- detect duplicates, contradictions, stale facts
- propose promotions and consolidations with provenance

## Phase 3 — Operator workflow
- add scripts for repeatable maintenance runs
- add examples and reviewable outputs
- support manual and scheduled execution

## Phase 4 — Hermes integration options
- evaluate skill-only workflow
- evaluate plugin surface
- evaluate memory-provider integration
- choose the smallest clean integration that works
