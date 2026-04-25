---
name: mneme-hermes
description: Audit Hermes built-in memory for capacity, duplicates, stale markers, directive phrasing, and possible secrets using the mneme-hermes CLI. Use before editing ~/.hermes/memories/MEMORY.md or USER.md.
version: 0.1.0
author: mneme-hermes contributors
license: UNLICENSED
metadata:
  hermes:
    tags: [hermes, memory, audit, provenance, hygiene]
    related_skills: [hermes-agent]
---

# Mneme-Hermes Memory Audit

Use this skill when a Hermes agent needs to inspect or improve Hermes built-in memory.

## When to use

- Before editing `~/.hermes/memories/MEMORY.md` or `USER.md`.
- When `USER.md` is near its character limit.
- When memory feels stale, duplicated, imperative, or noisy.
- Before scheduled memory cleanup or migration.

## Commands

From a checkout of `mneme-hermes`:

```bash
python3 scripts/mneme-hermes audit
```

Save a Markdown report:

```bash
python3 scripts/mneme-hermes audit --output output/memory-audit.md
```

Use JSON for automation:

```bash
python3 scripts/mneme-hermes audit --format json --output output/memory-audit.json
```

Create a backup before edits:

```bash
python3 scripts/mneme-hermes snapshot --output-dir output/snapshots
```

Audit another Hermes profile/home:

```bash
python3 scripts/mneme-hermes audit --home /path/to/.hermes
```

## Workflow

1. Run `audit`.
2. Read errors first, then warnings.
3. Run `snapshot` before changing memory files.
4. Edit memory manually through Hermes’ memory tool or direct file edits only when appropriate.
5. Re-run `audit` and compare.
6. Do not preserve secrets. Replace secrets with `[REDACTED]` and rotate credentials outside this tool.

## Boundaries

- The CLI does not rewrite memory automatically.
- It does not make semantic truth claims; stale/duplicate/conflict findings are review prompts.
- `snapshot` does not copy config by default because configs can contain secrets.
