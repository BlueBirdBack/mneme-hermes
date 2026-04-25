# mneme-hermes

[![CI](https://github.com/BlueBirdBack/mneme-hermes/actions/workflows/ci.yml/badge.svg)](https://github.com/BlueBirdBack/mneme-hermes/actions/workflows/ci.yml)

Mneme-Hermes is a **Hermes memory audit toolkit**: Mneme-style quality checks, snapshots, provenance notes, and agent-ready workflows for keeping long-term memory useful instead of noisy.

The repo includes a tiny, **stdlib-only** CLI that Hermes agents can run immediately against local Hermes memory files:

- `~/.hermes/memories/MEMORY.md`
- `~/.hermes/memories/USER.md`
- `~/.hermes/config.yaml` (detected by default, never copied unless requested)

## Quickstart for Hermes agents

From a checkout:

```bash
python3 scripts/mneme-hermes audit
```

Write a reviewable Markdown report:

```bash
python3 scripts/mneme-hermes audit --output output/memory-audit.md
```

Create a timestamped backup before editing memory:

```bash
python3 scripts/mneme-hermes snapshot --output-dir output/snapshots
```

If installed as a package, use the console script instead:

```bash
mneme-hermes audit
mneme-hermes snapshot --output-dir output/snapshots
```

## What the CLI does today

`audit` inspects Hermes memory files and reports:

- whether `MEMORY.md` and `USER.md` exist
- Hermes entry counts using the real `\n§\n` separator
- character usage against configured Hermes memory limits
- duplicate entries across memory files
- stale/conflict/TODO-style markers that need review
- directive-style phrasing that should be made declarative
- possible secret-like or prompt-injection-like lines, redacted in the report
- whether `~/.hermes/config.yaml` exists

Use `--strict` when you want CI-style exit codes: `0` clean, `1` warnings, `2` errors.

`snapshot` copies `MEMORY.md` and `USER.md` into a timestamped directory with a `manifest.json`. It does **not** copy config by default because configs may contain secrets. Use `--include-config` only when safe.

## Install / development

No runtime dependencies are required beyond Python 3.10+.

```bash
python3 -m unittest discover -s tests
```

Optional editable install:

```bash
python3 -m pip install -e .
mneme-hermes audit
```

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

## Project tracks

1. Git-aware wiki maintenance for Hermes-style research wikis
2. Mneme-inspired memory quality checks for Hermes memory and knowledge stores
3. Small, review-first CLI workflows agents can run safely

## Repo structure

- `mneme_hermes/cli.py` — stdlib-only CLI implementation
- `scripts/mneme-hermes` — run the CLI from a checkout without installing
- `tests/test_cli.py` — unittest coverage for audit/snapshot behavior
- `docs/agent-quickstart.md` — operational guide for Hermes agents
- `docs/hermes-memory-checks.md` — deterministic checks implemented by the CLI
- `docs/vision.md` — what Mneme-Hermes is trying to become
- `docs/roadmap.md` — phased development plan
- `docs/hermes-fit.md` — mapping Mneme ideas onto Hermes architecture
- `docs/repo-wiki-updater.md` — spec for git-aware wiki maintenance
- `docs/memory-quality-layer.md` — spec for Hermes memory-quality workflows

## Current status

Usable alpha. The CLI is intentionally conservative: it reports and snapshots, but it does not rewrite Hermes memory automatically.

Use it before memory edits, profile migrations, or cleanup passes.

## Credits

Built by Claw 🐾 for Hermes agents.
