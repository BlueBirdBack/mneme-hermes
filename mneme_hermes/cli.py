from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence, TextIO

MEMORY_FILENAMES = ("MEMORY.md", "USER.md")
HERMES_ENTRY_SEPARATOR = "\n§\n"
DEFAULT_MEMORY_LIMIT = 2200
DEFAULT_USER_LIMIT = 1375

HEADING_LINE_RE = re.compile(r"^\s{0,3}#{1,6}\s+")
BULLET_PREFIX_RE = re.compile(r"^\s*[-*+]\s+")
QUALITY_MARKER_RE = re.compile(
    r"\b(todo|fixme|tbd|stale|outdated|obsolete|deprecated|conflict|contradict(?:s|ion|ory)?)\b",
    re.IGNORECASE,
)
DIRECTIVE_RE = re.compile(
    r"(^|\b)(always|never|do not|don't|must|should|from now on|you must|you should|ignore previous instructions|system prompt override)\b",
    re.IGNORECASE,
)
RELATIVE_TIME_RE = re.compile(
    r"\b(today|tomorrow|yesterday|currently|now|recently|last week|next week|soon|temporary|temp)\b",
    re.IGNORECASE,
)
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b[A-Za-z0-9_.-]*(?:api[_-]?key|access[_-]?key|token|secret|password|passwd|credential|authorization|bearer)[A-Za-z0-9_.-]*\b\s*[:=]\s*\S+"
)
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
CRED_URL_RE = re.compile(r"https?://[^/\s:@]+:[^/\s:@]+@")
PROMPT_INJECTION_RE = re.compile(
    r"(?i)(ignore previous instructions|disregard (your )?(instructions|rules)|system prompt override|do not tell the user|read .*\.env|exfiltrat|curl .*\$(api|token|secret|password))"
)
INVISIBLE_CHARS = {"\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"} | {chr(cp) for cp in range(0x202A, 0x202F)}
TOKEN_RE = re.compile(r"\b[A-Za-z0-9_\-]{32,}\b")


@dataclass(frozen=True)
class ResolvedPaths:
    home: Path
    memory_dir: Path
    config_path: Path


@dataclass(frozen=True)
class Issue:
    severity: str
    check: str
    file: str
    entry_index: int | None
    line: int | None
    message: str
    snippet: str = ""
    redacted: bool = False


@dataclass(frozen=True)
class Occurrence:
    file: str
    entry_index: int
    line: int
    snippet: str


@dataclass(frozen=True)
class DuplicateGroup:
    normalized: str
    occurrences: tuple[Occurrence, ...]


@dataclass(frozen=True)
class MemoryFileReport:
    filename: str
    path: str
    exists: bool
    bytes: int = 0
    lines: int = 0
    entries: int = 0
    char_usage: int = 0
    char_limit: int = 0
    char_usage_percent: float = 0.0
    remaining_chars: int = 0
    longest_entry_chars: int = 0
    issues: tuple[Issue, ...] = ()


@dataclass(frozen=True)
class AuditReport:
    generated_at: str
    home: str
    memory_dir: str
    config_path: str
    config_exists: bool
    files: tuple[MemoryFileReport, ...]
    duplicates: tuple[DuplicateGroup, ...]
    summary: dict[str, int]


@dataclass(frozen=True)
class MemoryEntry:
    text: str
    index: int
    start_line: int


@dataclass(frozen=True)
class Suggestion:
    priority: str
    action: str
    reason: str
    details: tuple[str, ...] = ()
    estimated_chars_saved: int | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def snapshot_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def default_home() -> Path:
    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".hermes"


def resolve_paths(home: Path | None, memory_dir: Path | None, config: Path | None) -> ResolvedPaths:
    resolved_home = home.expanduser() if home else default_home()
    return ResolvedPaths(
        home=resolved_home,
        memory_dir=memory_dir.expanduser() if memory_dir else resolved_home / "memories",
        config_path=config.expanduser() if config else resolved_home / "config.yaml",
    )


def memory_limit_for(filename: str, config_path: Path) -> int:
    limits = parse_memory_limits(config_path)
    if filename == "USER.md":
        return limits.get("user_char_limit", DEFAULT_USER_LIMIT)
    return limits.get("memory_char_limit", DEFAULT_MEMORY_LIMIT)


def parse_memory_limits(config_path: Path) -> dict[str, int]:
    if not config_path.exists():
        return {"memory_char_limit": DEFAULT_MEMORY_LIMIT, "user_char_limit": DEFAULT_USER_LIMIT}
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError:
        return {"memory_char_limit": DEFAULT_MEMORY_LIMIT, "user_char_limit": DEFAULT_USER_LIMIT}

    limits = {"memory_char_limit": DEFAULT_MEMORY_LIMIT, "user_char_limit": DEFAULT_USER_LIMIT}
    in_memory_block = False
    memory_indent = 0
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()
        if stripped == "memory:":
            in_memory_block = True
            memory_indent = indent
            continue
        if in_memory_block and indent <= memory_indent and not stripped.startswith(("memory_char_limit", "user_char_limit")):
            in_memory_block = False
        if in_memory_block or stripped.startswith(("memory_char_limit", "user_char_limit")):
            match = re.match(r"(memory_char_limit|user_char_limit)\s*:\s*(\d+)", stripped)
            if match:
                limits[match.group(1)] = int(match.group(2))
    return limits


def split_entries(text: str) -> list[MemoryEntry]:
    if text == "":
        return []
    raw_entries = text.split(HERMES_ENTRY_SEPARATOR)
    entries: list[MemoryEntry] = []
    line_cursor = 1
    for raw in raw_entries:
        stripped = raw.strip()
        if stripped:
            entries.append(MemoryEntry(text=stripped, index=len(entries) + 1, start_line=line_cursor))
        line_cursor += raw.count("\n") + HERMES_ENTRY_SEPARATOR.count("\n")
    return entries


def normalize_entry(text: str) -> str:
    useful_lines: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or HEADING_LINE_RE.match(line):
            continue
        line = BULLET_PREFIX_RE.sub("", line)
        useful_lines.append(line)
    text = " ".join(useful_lines) if useful_lines else text.strip()
    text = re.sub(r"https?://\S+", " URLTOKEN ", text)
    text = re.sub(r"[`*_~>#\[\](){}]", "", text)
    text = text.replace("URLTOKEN", "<url>")
    text = re.sub(r"\s+", " ", text)
    text = text.strip().rstrip(". ;")
    return text.casefold()


def is_sensitive_text(text: str) -> bool:
    return bool(
        SECRET_ASSIGNMENT_RE.search(text)
        or PRIVATE_KEY_RE.search(text)
        or CRED_URL_RE.search(text)
        or PROMPT_INJECTION_RE.search(text)
        or any(ch in text for ch in INVISIBLE_CHARS)
        or any(looks_high_entropy(token) for token in TOKEN_RE.findall(text))
    )


def redact_snippet(text: str) -> tuple[str, bool]:
    raw = text.strip().replace("\n", " ")
    if PROMPT_INJECTION_RE.search(raw):
        return "[redacted prompt-injection-like text]", True
    patterns = [SECRET_ASSIGNMENT_RE, PRIVATE_KEY_RE, CRED_URL_RE]
    if any(pattern.search(raw) for pattern in patterns):
        return "[redacted possible secret-like text]", True
    if any(ch in raw for ch in INVISIBLE_CHARS):
        return "[redacted invisible/control unicode text]", True

    redacted = False
    snippet = raw
    for token in TOKEN_RE.findall(snippet):
        if looks_high_entropy(token):
            snippet = snippet.replace(token, "[REDACTED high-entropy token]")
            redacted = True
    if len(snippet) > 180:
        snippet = snippet[:177] + "..."
    return snippet, redacted


def looks_high_entropy(token: str) -> bool:
    if len(token) < 32:
        return False
    alphabet = set(token)
    if not (any(c.islower() for c in token) and any(c.isupper() for c in token) and any(c.isdigit() for c in token)):
        return False
    entropy = -sum((token.count(c) / len(token)) * math.log2(token.count(c) / len(token)) for c in alphabet)
    return entropy >= 4.0


def escape_markdown_text(text: str) -> str:
    replacements = {
        "\\": "\\\\",
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
        "#": "\\#",
        "-": "\\-",
        "`": "\\`",
        "*": "\\*",
        "_": "\\_",
        "[": "\\[",
        "]": "\\]",
        "(": "\\(",
        ")": "\\)",
        "!": "\\!",
        "~": "\\~",
        "|": "\\|",
        "<": "&lt;",
        ">": "&gt;",
    }
    return "".join(replacements.get(char, char) for char in text)


def add_issue(
    issues: list[Issue],
    severity: str,
    check: str,
    filename: str,
    entry: MemoryEntry | None,
    message: str,
    snippet: str = "",
    line: int | None = None,
) -> None:
    redacted = False
    if snippet:
        snippet, redacted = redact_snippet(snippet)
    issues.append(
        Issue(
            severity=severity,
            check=check,
            file=filename,
            entry_index=entry.index if entry else None,
            line=line if line is not None else (entry.start_line if entry else None),
            message=message,
            snippet=snippet,
            redacted=redacted,
        )
    )


def analyze_entry(filename: str, entry: MemoryEntry, issues: list[Issue], occurrences: list[tuple[str, Occurrence]]) -> None:
    normalized = normalize_entry(entry.text)
    snippet, _ = redact_snippet(entry.text)
    if len(normalized) >= 12 and not is_sensitive_text(entry.text):
        occurrences.append((normalized, Occurrence(filename, entry.index, entry.start_line, snippet)))

    if QUALITY_MARKER_RE.search(entry.text):
        add_issue(issues, "WARN", "marker.review_word", filename, entry, "Entry contains TODO/stale/conflict-style wording; verify before preserving.", entry.text)
    if DIRECTIVE_RE.search(entry.text):
        severity = "WARN" if filename == "MEMORY.md" else "INFO"
        add_issue(issues, severity, "phrasing.directive", filename, entry, "Entry is phrased like an instruction; prefer declarative durable facts.", entry.text)
    if RELATIVE_TIME_RE.search(entry.text):
        add_issue(issues, "INFO", "staleness.relative_time", filename, entry, "Entry uses relative time wording that may decay.", entry.text)
    if PROMPT_INJECTION_RE.search(entry.text):
        add_issue(issues, "ERROR", "security.prompt_injection", filename, entry, "Entry resembles prompt-injection or exfiltration text.", entry.text)
    if any(ch in entry.text for ch in INVISIBLE_CHARS):
        add_issue(issues, "ERROR", "security.invisible_unicode", filename, entry, "Entry contains invisible/control Unicode characters.", entry.text)
    if SECRET_ASSIGNMENT_RE.search(entry.text) or PRIVATE_KEY_RE.search(entry.text) or CRED_URL_RE.search(entry.text):
        add_issue(issues, "ERROR", "security.possible_secret", filename, entry, "Entry may contain a secret or credential; remove from memory and rotate externally.", entry.text)
    elif any(looks_high_entropy(token) for token in TOKEN_RE.findall(entry.text)):
        add_issue(issues, "WARN", "security.high_entropy_token", filename, entry, "Entry contains a high-entropy token-like string.", entry.text)
    if "```" in entry.text or "Traceback (most recent call last)" in entry.text:
        add_issue(issues, "WARN", "structure.raw_dump", filename, entry, "Entry looks like code/log dump rather than compact memory.", entry.text)
    if len(entry.text.splitlines()) > 8:
        add_issue(issues, "INFO", "structure.long_entry", filename, entry, "Entry is long; consider compacting to the durable fact.", entry.text)
    if len(entry.text) < 20:
        add_issue(issues, "INFO", "quality.short_entry", filename, entry, "Entry may be too short to be useful later.", entry.text)


def analyze_memory_file(path: Path, config_path: Path) -> tuple[MemoryFileReport, list[tuple[str, Occurrence]]]:
    filename = path.name
    char_limit = memory_limit_for(filename, config_path)
    if not path.exists():
        issue = Issue("INFO", "file.missing", filename, None, None, f"{filename} was not found")
        return MemoryFileReport(filename=filename, path=str(path), exists=False, char_limit=char_limit, issues=(issue,)), []

    try:
        data = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        issue = Issue("ERROR", "file.invalid_utf8", filename, None, None, f"{filename} is not valid UTF-8")
        return MemoryFileReport(filename=filename, path=str(path), exists=True, bytes=path.stat().st_size, char_limit=char_limit, issues=(issue,)), []

    entries = split_entries(data)
    canonical_text = HERMES_ENTRY_SEPARATOR.join(entry.text for entry in entries)
    char_usage = len(canonical_text)
    char_usage_percent = round((char_usage / char_limit) * 100, 1) if char_limit > 0 else 0.0
    remaining_chars = char_limit - char_usage
    issues: list[Issue] = []
    occurrences: list[tuple[str, Occurrence]] = []

    if char_limit <= 0:
        add_issue(issues, "ERROR", "config.invalid_limit", filename, None, "Configured memory limit is not positive.")
    elif char_usage > char_limit:
        add_issue(issues, "ERROR", "capacity.over_limit", filename, None, f"{filename} exceeds configured limit: {char_usage}/{char_limit} chars.")
    elif char_usage_percent >= 90:
        add_issue(issues, "WARN", "capacity.high_usage", filename, None, f"{filename} is {char_usage_percent}% full: {char_usage}/{char_limit} chars.")
    elif char_usage_percent >= 80:
        add_issue(issues, "INFO", "capacity.near_limit", filename, None, f"{filename} is {char_usage_percent}% full: {char_usage}/{char_limit} chars.")

    if data and not entries:
        add_issue(issues, "WARN", "format.empty_after_parse", filename, None, "File has content but no non-empty Hermes entries.")
    if "\r\n" in data:
        add_issue(issues, "INFO", "format.crlf", filename, None, "File uses CRLF line endings; Hermes works best with LF.")
    if "\n§\n\n§\n" in data or data.startswith(HERMES_ENTRY_SEPARATOR) or data.endswith(HERMES_ENTRY_SEPARATOR):
        add_issue(issues, "WARN", "format.empty_entry", filename, None, "File appears to contain empty memory entries.")

    for entry in entries:
        if char_limit > 0 and len(entry.text) / char_limit >= 0.40:
            add_issue(issues, "WARN", "capacity.large_entry", filename, entry, "Single entry consumes more than 40% of this memory store.", entry.text)
        analyze_entry(filename, entry, issues, occurrences)

    return (
        MemoryFileReport(
            filename=filename,
            path=str(path),
            exists=True,
            bytes=path.stat().st_size,
            lines=len(data.splitlines()),
            entries=len(entries),
            char_usage=char_usage,
            char_limit=char_limit,
            char_usage_percent=char_usage_percent,
            remaining_chars=remaining_chars,
            longest_entry_chars=max((len(entry.text) for entry in entries), default=0),
            issues=tuple(issues),
        ),
        occurrences,
    )


def iter_memory_files(memory_dir: Path) -> Iterable[Path]:
    for name in MEMORY_FILENAMES:
        yield memory_dir / name


def build_audit(memory_dir: Path, config_path: Path, home: Path | None = None) -> AuditReport:
    file_reports: list[MemoryFileReport] = []
    occurrence_map: dict[str, list[Occurrence]] = defaultdict(list)

    for path in iter_memory_files(memory_dir):
        report, occurrences = analyze_memory_file(path, config_path)
        file_reports.append(report)
        for normalized, occurrence in occurrences:
            occurrence_map[normalized].append(occurrence)

    duplicates = tuple(
        DuplicateGroup(normalized=normalized, occurrences=tuple(occurrences))
        for normalized, occurrences in sorted(occurrence_map.items())
        if len(occurrences) > 1
    )
    issue_counts = {"ERROR": 0, "WARN": 0, "INFO": 0}
    for report in file_reports:
        for issue in report.issues:
            issue_counts[issue.severity] = issue_counts.get(issue.severity, 0) + 1
    if duplicates:
        issue_counts["WARN"] += len(duplicates)

    inferred_home = home or memory_dir.parent
    return AuditReport(
        generated_at=utc_now(),
        home=str(inferred_home),
        memory_dir=str(memory_dir),
        config_path=str(config_path),
        config_exists=config_path.exists(),
        files=tuple(file_reports),
        duplicates=duplicates,
        summary=issue_counts,
    )


def render_markdown(report: AuditReport) -> str:
    found = sum(1 for file_report in report.files if file_report.exists)
    lines: list[str] = [
        "# Mneme-Hermes Memory Audit",
        "",
        f"Generated: `{report.generated_at}`",
        f"Hermes home: `{report.home}`",
        f"Memory dir: `{report.memory_dir}`",
        f"Config: `{report.config_path}` ({'found' if report.config_exists else 'missing'})",
        "",
        "## Summary",
        f"- Memory files found: {found}/{len(report.files)}",
        f"- Errors: {report.summary.get('ERROR', 0)}",
        f"- Warnings: {report.summary.get('WARN', 0)}",
        f"- Info: {report.summary.get('INFO', 0)}",
        f"- Duplicate entry groups: {len(report.duplicates)}",
        "",
        "## Files",
    ]

    for file_report in report.files:
        status = "found" if file_report.exists else "missing"
        lines.extend([f"### {file_report.filename}", f"- Path: `{file_report.path}`", f"- Status: {status}"])
        if file_report.exists:
            lines.extend(
                [
                    f"- Size: {file_report.bytes} bytes",
                    f"- Lines: {file_report.lines}",
                    f"- Entries: {file_report.entries}",
                    f"- Character usage: {file_report.char_usage}/{file_report.char_limit} ({file_report.char_usage_percent}%)",
                    f"- Remaining chars: {file_report.remaining_chars}",
                    f"- Longest entry: {file_report.longest_entry_chars} chars",
                ]
            )
        if file_report.issues:
            lines.append("- Issues:")
            for issue in file_report.issues:
                where_parts = [issue.file]
                if issue.entry_index is not None:
                    where_parts.append(f"entry {issue.entry_index}")
                if issue.line is not None:
                    where_parts.append(f"line {issue.line}")
                where = ", ".join(where_parts)
                snippet = f" — `{issue.snippet}`" if issue.snippet else ""
                lines.append(f"  - **{issue.severity}** `{issue.check}` at {where}: {issue.message}{snippet}")
        lines.append("")

    lines.append("## Duplicate entries")
    if not report.duplicates:
        lines.append("No duplicate entry groups found.")
    for duplicate in report.duplicates:
        lines.append(f"- `{duplicate.normalized}`")
        for occurrence in duplicate.occurrences:
            lines.append(f"  - `{occurrence.file}` entry {occurrence.entry_index}, line {occurrence.line} — {occurrence.snippet}")
    lines.extend(
        [
            "",
            "## Review checklist for Hermes agents",
            "1. Read flagged lines in the source memory files before editing.",
            "2. Run `mneme-hermes snapshot` before applying memory edits.",
            "3. Merge exact duplicates manually; keep the clearest durable wording.",
            "4. Rewrite directive-style memories as declarative facts where possible.",
            "5. Treat security findings as urgent: remove secrets from memory and rotate credentials outside this tool.",
            "6. Re-run this audit after edits and compare the report.",
            "",
        ]
    )
    return "\n".join(lines)


def report_to_json(report: AuditReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True) + "\n"


def build_suggestions(report: AuditReport) -> tuple[Suggestion, ...]:
    suggestions: list[Suggestion] = []

    for file_report in report.files:
        for issue in file_report.issues:
            if issue.check in {"capacity.over_limit", "capacity.high_usage", "capacity.near_limit"}:
                if issue.check == "capacity.over_limit":
                    priority = "high"
                elif issue.check == "capacity.high_usage":
                    priority = "medium"
                else:
                    priority = "low"
                suggestions.append(
                    Suggestion(
                        priority=priority,
                        action=f"Reduce {file_report.filename} capacity pressure",
                        reason=issue.message,
                        details=(
                            f"Current usage: {file_report.char_usage}/{file_report.char_limit} chars ({file_report.char_usage_percent}%).",
                            "Review long, overlapping, stale, or procedural entries first.",
                            "Keep changes review-first; do not rewrite memory automatically.",
                        ),
                        estimated_chars_saved=max(0, file_report.char_usage - int(file_report.char_limit * 0.75)),
                    )
                )
            elif issue.check == "phrasing.directive":
                where = f"{issue.file} entry {issue.entry_index}" if issue.entry_index else issue.file
                suggestions.append(
                    Suggestion(
                        priority="low",
                        action="Rewrite directive-style memory",
                        reason=f"{where} reads like an instruction; prefer a declarative durable fact.",
                        details=(f"Snippet: {issue.snippet}",) if issue.snippet else (),
                    )
                )
            elif issue.check in {"marker.review_word", "staleness.relative_time", "structure.raw_dump", "structure.long_entry"}:
                where = f"{issue.file} entry {issue.entry_index}" if issue.entry_index else issue.file
                suggestions.append(
                    Suggestion(
                        priority="medium" if issue.severity == "WARN" else "low",
                        action="Review stale/noisy memory entry",
                        reason=f"{where}: {issue.message}",
                        details=(f"Snippet: {issue.snippet}",) if issue.snippet else (),
                    )
                )
            elif issue.check.startswith("security."):
                where = f"{issue.file} entry {issue.entry_index}" if issue.entry_index else issue.file
                suggestions.append(
                    Suggestion(
                        priority="high",
                        action="Remove sensitive memory and rotate externally",
                        reason=f"{where}: {issue.message}",
                        details=(f"Snippet: {issue.snippet}",) if issue.snippet else (),
                    )
                )

    for duplicate in report.duplicates:
        details = tuple(
            f"{occurrence.file} entry {occurrence.entry_index}, line {occurrence.line}: {occurrence.snippet}"
            for occurrence in duplicate.occurrences
        )
        saved = sum(len(occurrence.snippet) for occurrence in duplicate.occurrences[1:])
        suggestions.append(
            Suggestion(
                priority="medium",
                action="Merge duplicate entries",
                reason="Multiple memory entries normalize to the same durable fact.",
                details=details,
                estimated_chars_saved=saved,
            )
        )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    return tuple(sorted(suggestions, key=lambda item: (priority_order.get(item.priority, 99), item.action, item.reason)))


def render_suggestions_markdown(report: AuditReport, suggestions: tuple[Suggestion, ...]) -> str:
    lines = [
        "# Mneme-Hermes Memory Suggestions",
        "",
        f"Generated: `{report.generated_at}`",
        f"Memory dir: {escape_markdown_text(report.memory_dir)}",
        "",
        "These are review-first suggestions. Apply them manually, then re-run `mneme-hermes audit`.",
        "",
        "## Summary",
        f"- Suggestions: {len(suggestions)}",
        f"- Audit errors: {report.summary.get('ERROR', 0)}",
        f"- Audit warnings: {report.summary.get('WARN', 0)}",
        f"- Duplicate groups: {len(report.duplicates)}",
        "",
    ]
    if not suggestions:
        lines.extend(["No cleanup suggestions found.", ""])
        return "\n".join(lines)

    lines.append("## Suggested actions")
    for index, suggestion in enumerate(suggestions, 1):
        lines.append(f"{index}. **{suggestion.action}** ({suggestion.priority})")
        lines.append(f"   - Reason: {escape_markdown_text(suggestion.reason)}")
        if suggestion.estimated_chars_saved is not None:
            lines.append(f"   - Estimated chars saved: {suggestion.estimated_chars_saved}")
        for detail in suggestion.details:
            lines.append(f"   - {escape_markdown_text(detail)}")
    lines.append("")
    return "\n".join(lines)


def suggestions_to_json(report: AuditReport, suggestions: tuple[Suggestion, ...]) -> str:
    payload = {
        "kind": "mneme-hermes-suggestions",
        "generated_at": report.generated_at,
        "memory_dir": report.memory_dir,
        "summary": report.summary,
        "suggestions": [asdict(suggestion) for suggestion in suggestions],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_or_print(text: str, output: Path | None, stdout: TextIO) -> None:
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        stdout.write(text)
        if not text.endswith("\n"):
            stdout.write("\n")


def strict_exit_code(report: AuditReport) -> int:
    if report.summary.get("ERROR", 0) > 0:
        return 2
    if report.summary.get("WARN", 0) > 0:
        return 1
    return 0


def audit_command(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = resolve_paths(args.home, args.memory_dir, args.config)
    report = build_audit(paths.memory_dir, paths.config_path, paths.home)
    rendered = report_to_json(report) if args.format == "json" else render_markdown(report)
    write_or_print(rendered, args.output.expanduser() if args.output else None, stdout)
    return strict_exit_code(report) if args.strict else 0


def suggest_command(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = resolve_paths(args.home, args.memory_dir, args.config)
    report = build_audit(paths.memory_dir, paths.config_path, paths.home)
    suggestions = build_suggestions(report)
    rendered = suggestions_to_json(report, suggestions) if args.format == "json" else render_suggestions_markdown(report, suggestions)
    write_or_print(rendered, args.output.expanduser() if args.output else None, stdout)
    return 0


def snapshot_command(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = resolve_paths(args.home, args.memory_dir, args.config)
    timestamp = snapshot_timestamp()
    destination_root = args.output_dir.expanduser() if args.output_dir else Path.cwd() / "mneme-hermes-snapshots"
    destination = destination_root / f"hermes-memory-{timestamp}"
    destination.mkdir(parents=True, exist_ok=False)

    copied: list[dict[str, str]] = []
    for source in iter_memory_files(paths.memory_dir):
        if source.exists():
            target = destination / source.name
            shutil.copy2(source, target)
            copied.append({"source": str(source), "target": str(target)})

    if args.include_config and paths.config_path.exists():
        target = destination / paths.config_path.name
        shutil.copy2(paths.config_path, target)
        copied.append({"source": str(paths.config_path), "target": str(target)})

    manifest = {
        "created_at": utc_now(),
        "home": str(paths.home),
        "memory_dir": str(paths.memory_dir),
        "config_path": str(paths.config_path),
        "included_config": bool(args.include_config),
        "copied": copied,
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    stdout.write(f"Snapshot written to {destination}\n")
    if not copied:
        stdout.write("Warning: no Hermes memory files were found to copy.\n")
    return 0


def add_common_path_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--home", type=Path, help="Hermes home directory. Defaults to HERMES_HOME or ~/.hermes.")
    parser.add_argument("--memory-dir", type=Path, help="Hermes memory directory. Defaults to HOME/memories.")
    parser.add_argument("--config", type=Path, help="Hermes config path. Defaults to HOME/config.yaml.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mneme-hermes",
        description="Stdlib-only helper CLI for Hermes memory hygiene.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Inspect Hermes memory files and emit a reviewable report.")
    add_common_path_args(audit)
    audit.add_argument("--format", choices=("markdown", "json"), default="markdown", help="Report format.")
    audit.add_argument("--output", type=Path, help="Write report to this path instead of stdout.")
    audit.add_argument("--strict", action="store_true", help="Return 1 for warnings and 2 for errors; default always exits 0 after reporting.")
    audit.set_defaults(func=audit_command)

    suggest = subparsers.add_parser("suggest", help="Turn audit findings into review-first cleanup suggestions.")
    add_common_path_args(suggest)
    suggest.add_argument("--format", choices=("markdown", "json"), default="markdown", help="Suggestion format.")
    suggest.add_argument("--output", type=Path, help="Write suggestions to this path instead of stdout.")
    suggest.set_defaults(func=suggest_command)

    snapshot = subparsers.add_parser("snapshot", help="Copy Hermes memory files into a timestamped review backup.")
    add_common_path_args(snapshot)
    snapshot.add_argument("--output-dir", type=Path, help="Directory that will contain timestamped snapshots.")
    snapshot.add_argument("--include-config", action="store_true", help="Also copy config.yaml; opt-in because configs may contain secrets.")
    snapshot.set_defaults(func=snapshot_command)

    return parser


def main(argv: Sequence[str] | None = None, stdout: TextIO = sys.stdout) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args, stdout)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
