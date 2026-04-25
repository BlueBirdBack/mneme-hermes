# Hermes Memory Checks

Mneme-Hermes starts as a conservative memory quality layer for Hermes. It is intentionally read-only unless you run `snapshot`, which copies files for backup.

## Files inspected

By default the CLI resolves paths in this order:

1. `--home`, `--memory-dir`, and `--config` flags
2. `HERMES_HOME`
3. `~/.hermes`

It inspects:

- `memories/MEMORY.md`
- `memories/USER.md`
- `config.yaml` for memory character limits

## Hermes entry format

Hermes built-in memory entries are separated by the exact delimiter:

```text
\n§\n
```

The audit uses that delimiter for entry counts and character usage.

## Checks today

### Capacity

- Reads `memory.memory_char_limit` and `memory.user_char_limit` from `config.yaml` when present.
- Falls back to Hermes defaults:
  - `MEMORY.md`: `2200` chars
  - `USER.md`: `1375` chars
- Reports usage, remaining chars, and oversized single entries.

### Duplicates

- Normalizes headings, bullet prefixes, Markdown emphasis, URLs, whitespace, and case.
- Reports duplicate entries across `MEMORY.md` and `USER.md`.
- Does not auto-delete anything.

### Security hygiene

Reports and redacts likely sensitive or hostile memory content:

- secret-like assignments such as `token: ...` or `api_key=...`
- private key blocks
- credentialed URLs
- high-entropy token-like strings
- prompt-injection or exfiltration-like text
- invisible/control Unicode characters

### Memory quality

Flags entries that may need manual review:

- TODO/stale/conflict wording
- directive-style phrasing like “always”, “never”, “you must”
- relative time wording like “today”, “currently”, “soon”
- code/log dumps
- very long or very short entries

## Exit behavior

Default mode reports findings and exits `0` so agents can use it inside exploratory workflows.

Use strict mode for CI or scheduled checks:

```bash
python3 scripts/mneme-hermes audit --strict
```

Strict exit codes:

- `0`: no warnings or errors
- `1`: warning-level findings
- `2`: error-level findings

## Safe operating rule

Mneme-Hermes should produce evidence and review queues, not silently rewrite durable memory. Automatic fixing can come later, behind explicit backups and narrow rules.
