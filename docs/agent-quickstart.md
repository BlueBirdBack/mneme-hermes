# Agent Quickstart

This repo is useful when a Hermes agent needs a fast, reviewable health check of local Hermes memory without installing extra dependencies or touching secrets.

## Default Hermes paths

- Memory directory: `~/.hermes/memories/`
- Core memory file: `~/.hermes/memories/MEMORY.md`
- User memory file: `~/.hermes/memories/USER.md`
- Config path: `~/.hermes/config.yaml`

## First safe commands

Run from a checkout:

```bash
python3 scripts/mneme-hermes audit
```

Save a report:

```bash
python3 scripts/mneme-hermes audit --output output/memory-audit.md
```

Back up memory before editing:

```bash
python3 scripts/mneme-hermes snapshot --output-dir output/snapshots
```

Use custom paths when operating on fixtures or another Hermes home:

```bash
python3 scripts/mneme-hermes audit \
  --memory-dir /path/to/.hermes/memories \
  --config /path/to/.hermes/config.yaml
```

## Review workflow

1. Run `audit` and read the `Summary`, `Files`, and `Duplicate bullets` sections.
2. Run `snapshot` before making any memory edits.
3. Open the source memory file at each flagged line.
4. Merge duplicates manually; keep concise durable facts.
5. Resolve `stale`, `outdated`, `conflict`, and `contradiction` markers only after checking evidence.
6. Remove possible secrets from memory and rotate exposed credentials outside this tool.
7. Re-run `audit` after edits and compare the report.

## Suggested workflow

```bash
python3 scripts/mneme-hermes audit --output output/memory-audit.md
python3 scripts/mneme-hermes suggest --output output/memory-suggestions.md
python3 scripts/mneme-hermes snapshot --output-dir output/snapshots
```

Apply only reviewed memory edits, then verify:

```bash
python3 scripts/mneme-hermes audit --strict
```

## JSON and strict mode for automation

```bash
python3 scripts/mneme-hermes audit --format json --output output/memory-audit.json
python3 scripts/mneme-hermes audit --strict
```

Default `audit` exits `0` after reporting. `--strict` exits `1` when warnings exist and `2` when errors exist.

The JSON shape mirrors the Markdown report: generated timestamp, detected paths, configured capacity, per-file metrics/issues, and duplicate entry groups.

## Safety boundaries

- The CLI does not rewrite memory files.
- `snapshot` copies only `MEMORY.md` and `USER.md` by default.
- Config copying is opt-in via `--include-config` because configs may contain secrets.
- Possible secret-like report lines are redacted.
