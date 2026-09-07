#!/usr/bin/env python3
"""Vault linter.

One copy lives in each repo as scripts/lint.py. The repo name is derived from
the directory that contains scripts/, so the file is byte-identical everywhere
and needs no per-repo configuration.

Usage:
    python3 scripts/lint.py [--quiet]

Exit status is 0 when the repo is clean and 1 when any error was reported.

Stdlib only, deliberately. The vault must stay checkable on a machine with
nothing installed but Python.
"""

from __future__ import annotations

import argparse
import subprocess
import datetime as dt
import re
import sys
from pathlib import Path

# One copy of this file lives in kb-base. Each repo's scripts/lint.py imports it
# and calls main(local=<its own rules>). The repo being linted is the git work
# tree the command runs in — never the location of this file.
BASE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT: Path = Path(".")
REPO_NAME = ""


def find_repo_root() -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("lint.py: run it inside a vault repo (the working directory is not a git work tree)")
    return Path(out.stdout.strip())

# Directories that hold no notes and are never checked as notes.
# Machinery, not notes. `setup/` holds launchd plists, shell config and the
# operational docs symlinked to the vault root — none of which carry
# frontmatter, and all of which would otherwise be linted as notes.
SKIP_DIRS = {".git", ".githooks", "_templates", "scripts", "setup",
             "node_modules"}

# Files that live in a repo but are documentation, not notes: no frontmatter
# is expected and none is required.
DOC_FILES = {"AGENTS.md", "CLAUDE.md", "README.md", "RULES.md",
             "WORKING-RULES.md"}

REQUIRED_FIELDS = ("id", "title", "repo", "tags", "created", "updated")

# Controlled tag vocabulary. One tag per line; blank lines and # comments
# ignored. Absent file means the check is skipped, so a repo can opt out.
TAGS_FILE = BASE_ROOT / "tags.txt"
MAX_TAGS = 5
MIN_TOPIC_LINKS = 3      # advisory: see the 'topic' rule in main()

# GitHub hard-blocks a single file over 100MB and warns at 50MB; its recommended
# whole-repo size is 1GB. A note vault should never come close, so anything this
# large is almost certainly an attachment committed by accident — and once it is
# in history the only remedy is a history rewrite. Fail early instead.
MAX_FILE_BYTES = 25 * 1024 * 1024
WARN_FILE_BYTES = 5 * 1024 * 1024
NEVER_COMMIT_SUFFIXES = {".mov", ".mp4", ".zip", ".dmg", ".iso", ".sqlite", ".db"}


def load_vocabulary() -> set[str] | None:
    if not TAGS_FILE.exists():
        return None
    return {
        line.strip()
        for line in TAGS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

# Crockford base32, excluding I, L, O and U.
ULID_RE = re.compile(r"^[0-7][0-9A-HJKMNP-TV-Z]{25}$")

# [[slug]] and [[slug|display text]]. Not matched inside fenced or inline code.
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")

# Inline code spans are blanked before link resolution so that documentation can
# write `[[slug]]` as an example without the linter chasing it.
INLINE_CODE_RE = re.compile(r"`+[^`]*`+")

# A line carrying this marker is exempt from the secret and hostname scans.
# Needed so AGENTS.md can document what a forbidden pattern looks like.
ALLOW_MARKER = "lint:allow"

SECRET_PATTERNS = [
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    # Separator optional: `aws configure set aws_secret_access_key 'KEY'` is the
    # CLI form and carried a real key past the [:=]-only version on 2026-09-06.
    ("AWS session/secret key", re.compile(r"(?i)\baws_(?:secret|session)\w*\s*[:=]?\s*['\"]?[A-Za-z0-9/+=]{16,}")),
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("GLM/Zhipu API key", re.compile(r"\b[0-9a-f]{32}\.[A-Za-z0-9]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[0-9A-Za-z\-]{10,}")),
    ("private key block", re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
    ("inline credential", re.compile(
        r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*"
        r"['\"]?[^\s'\"<>{}$]{8,}")),
]

# public/ only. RFC1918 ranges and internal-only hostname suffixes.
PRIVATE_IP_RE = re.compile(
    r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b")
INTERNAL_HOST_RE = re.compile(r"\b[a-z0-9][a-z0-9\-]*\.(?:internal|local|lan)\b", re.I)


class Problem:
    """A lint finding. Warnings are advisory: they print but never fail the run,
    so a pre-commit hook still lets the commit through. Use one where the rule
    expresses a habit worth keeping rather than an invariant worth enforcing."""

    __slots__ = ("path", "line", "message", "warning")

    def __init__(self, path: Path, line: int, message: str,
                 warning: bool = False) -> None:
        self.path = path
        self.line = line
        self.message = message
        self.warning = warning

    def render(self) -> str:
        rel = self.path.relative_to(REPO_ROOT)
        where = f"{rel}:{self.line}" if self.line else str(rel)
        prefix = "warning: " if self.warning else ""
        return f"{where}: {prefix}{self.message}"


def split_frontmatter(text: str) -> tuple[dict[str, str], str | None]:
    """Return (fields, error). Line numbers for body problems come from
    body_lines_outside_code, which walks the whole file."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "missing YAML frontmatter (file must start with ---)"

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            end = i
            break
    if end is None:
        return {}, "frontmatter is never closed with ---"

    fields: dict[str, str] = {}
    pending_key: str | None = None
    collected: list[str] = []

    for raw in lines[1:end]:
        if not raw.strip():
            continue
        # Block-sequence item belonging to the previous key.
        if raw.lstrip().startswith("- ") and pending_key:
            collected.append(raw.lstrip()[2:].strip())
            continue
        if pending_key and collected:
            fields[pending_key] = ", ".join(collected)
            collected = []
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_\-]*)\s*:\s*(.*)$", raw)
        if not m:
            pending_key = None
            continue
        key, value = m.group(1), m.group(2).strip()
        if value:
            fields[key] = value.strip("\"'")
            pending_key = None
        else:
            pending_key = key
    if pending_key and collected:
        fields[pending_key] = ", ".join(collected)

    return fields, None


def strip_inline_code(line: str) -> str:
    """Blank out inline code spans, preserving length so columns stay honest."""
    return INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), line)


def parse_tags(value: str) -> list[str]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [t.strip().strip("\"'") for t in value.split(",") if t.strip()]


def tags_of(path: Path) -> list[str]:
    """Tags of another note, parsed the same way its own lint pass would."""
    fields, err = split_frontmatter(path.read_text(encoding="utf-8"))
    return [] if err else parse_tags(fields.get("tags", ""))


def check_date(value: str) -> str | None:
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return "must be an ISO date (YYYY-MM-DD)"
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return f"is not a real calendar date ({value})"
    return None


def body_lines_outside_code(text: str):
    """Yield (lineno, line) for body lines, skipping fenced code blocks."""
    in_fence = False
    fence = ""
    for idx, line in enumerate(text.splitlines()):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence, fence = True, marker
            elif marker == fence:
                in_fence = False
            continue
        if in_fence:
            continue
        yield idx + 1, line


def check_file_sizes() -> list[Problem]:
    """Guard against committing something that cannot be removed later.

    Encrypted repos make this worse: git-crypt derives its nonce from the
    plaintext, so any edit rewrites the whole ciphertext and git cannot delta
    it. A large file in an encrypted repo costs its full size on every commit.
    """
    problems: list[Problem] = []
    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(REPO_ROOT)
        if ".git" in rel.parts:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_FILE_BYTES:
            problems.append(Problem(path, 0,
                f"file is {size / 1024 / 1024:.1f}MB, over the {MAX_FILE_BYTES // 1024 // 1024}MB "
                "limit — use an external store; a committed blob needs a history rewrite to remove"))
        elif size > WARN_FILE_BYTES:
            problems.append(Problem(path, 0,
                f"file is {size / 1024 / 1024:.1f}MB, unusually large for a note vault — "
                "confirm it belongs in git"))
        if path.suffix.lower() in NEVER_COMMIT_SUFFIXES:
            problems.append(Problem(path, 0,
                f"'{path.suffix}' files do not belong in a note vault"))
    return problems


def collect_notes() -> list[Path]:
    notes = []
    for path in sorted(REPO_ROOT.rglob("*.md")):
        rel = path.relative_to(REPO_ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        notes.append(path)
    return notes


def main(local=None) -> int:
    """Lint the repo the command runs in. `local(repo_root, notes) -> [Problem]`
    is the repo's own rule set, passed in by <repo>/scripts/lint.py."""
    global REPO_ROOT, REPO_NAME
    REPO_ROOT = find_repo_root()
    REPO_NAME = REPO_ROOT.name
    ap = argparse.ArgumentParser(description=f"Lint the '{REPO_NAME}' vault repo.")
    ap.add_argument("--quiet", action="store_true", help="print only problems")
    args = ap.parse_args()

    problems: list[Problem] = []
    notes = collect_notes()
    vocabulary = load_vocabulary()
    problems.extend(check_file_sizes())

    # Slug index for wikilink resolution: filename stem -> paths.
    slugs: dict[str, list[Path]] = {}
    for path in notes:
        slugs.setdefault(path.stem, []).append(path)

    seen_ids: dict[str, Path] = {}
    checked = 0

    for path in notes:
        rel = path.relative_to(REPO_ROOT)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            problems.append(Problem(path, 0, "file is not valid UTF-8"))
            continue

        is_doc = path.name in DOC_FILES and path.parent == REPO_ROOT

        if not is_doc:
            checked += 1
            fields, fm_error = split_frontmatter(text)
            if fm_error:
                problems.append(Problem(path, 1, fm_error))
            else:
                for key in REQUIRED_FIELDS:
                    if key not in fields or not fields[key].strip():
                        problems.append(Problem(path, 1, f"frontmatter is missing '{key}'"))

                note_id = fields.get("id", "").strip()
                if note_id:
                    if not ULID_RE.match(note_id):
                        problems.append(Problem(path, 1, f"'id' is not a valid ULID: {note_id}"))
                    elif note_id in seen_ids:
                        first = seen_ids[note_id].relative_to(REPO_ROOT)
                        problems.append(Problem(path, 1, f"duplicate id, already used by {first}"))
                    else:
                        seen_ids[note_id] = path

                declared = fields.get("repo", "").strip()
                if declared and declared != REPO_NAME:
                    problems.append(Problem(
                        path, 1,
                        f"'repo: {declared}' does not match this repo ('{REPO_NAME}')"))

                for key in ("created", "updated"):
                    value = fields.get(key, "").strip()
                    if value:
                        err = check_date(value)
                        if err:
                            problems.append(Problem(path, 1, f"'{key}' {err}"))
                c, u = fields.get("created", "").strip(), fields.get("updated", "").strip()
                if c and u and u < c:
                    problems.append(Problem(path, 1, f"'updated' ({u}) precedes 'created' ({c})"))

                if "tags" in fields:
                    tags = parse_tags(fields["tags"])
                    if not tags:
                        problems.append(Problem(path, 1, "'tags' is present but empty"))
                    elif len(tags) > MAX_TAGS:
                        problems.append(Problem(
                            path, 1,
                            f"{len(tags)} tags, maximum is {MAX_TAGS} — "
                            "a note needing more has not been split"))
                    if vocabulary is not None:
                        for tag in tags:
                            if tag not in vocabulary:
                                problems.append(Problem(
                                    path, 1,
                                    f"tag '{tag}' is not in tags.txt — add it "
                                    "deliberately or use an existing one"))

            # Wikilinks must resolve inside this repo.
            for lineno, line in body_lines_outside_code(text):
                for m in WIKILINK_RE.finditer(strip_inline_code(line)):
                    target = m.group(1).strip()
                    if target not in slugs:
                        problems.append(Problem(
                            path, lineno, f"[[{target}]] does not resolve in this repo"))

            # A note tagged 'position' must link a note tagged 'thesis'.
            # Anchored on TAGS rather than paths so the rule holds wherever the
            # note lives — a folder rename can no longer silently disable it,
            # and no third directory level is needed to express it.
            if "position" in parse_tags(fields.get("tags", "")):
                linked = {m.group(1).strip()
                          for _, line in body_lines_outside_code(text)
                          for m in WIKILINK_RE.finditer(strip_inline_code(line))}
                if not any("thesis" in tags_of(q)
                           for t in linked for q in slugs.get(t, [])):
                    problems.append(Problem(
                        path, 1,
                        "note tagged 'position' does not link a note tagged 'thesis'"))

            # A note tagged 'topic' synthesises other notes, so it must actually
            # reach them. Advisory, not enforced: a topic note is often written
            # before the notes it will gather, and blocking that commit would
            # just push people to skip the tag. Three is the point at which a
            # note is doing synthesis rather than cross-referencing.
            if "topic" in parse_tags(fields.get("tags", "")):
                linked = {m.group(1).strip()
                          for _, line in body_lines_outside_code(text)
                          for m in WIKILINK_RE.finditer(strip_inline_code(line))}
                if len(linked) < MIN_TOPIC_LINKS:
                    problems.append(Problem(
                        path, 1,
                        f"note tagged 'topic' links {len(linked)} note(s); "
                        f"a topic note should gather at least {MIN_TOPIC_LINKS}",
                        warning=True))

        # Secret scan runs on every markdown file, docs included.
        for lineno, line in enumerate(text.splitlines(), start=1):
            if ALLOW_MARKER in line:
                continue
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    problems.append(Problem(path, lineno, f"possible {label} committed"))

    # The repo's own rules — the delta, the way AGENTS.md is the delta over
    # RULES.md — join this report, so there is one summary line and one exit code.
    if local is not None:
        problems.extend(local(REPO_ROOT, notes))

    for problem in sorted(problems, key=lambda p: (str(p.path), p.line)):
        print(problem.render(), file=sys.stderr)

    errors = [p for p in problems if not p.warning]
    warnings = [p for p in problems if p.warning]
    warn_note = f", {len(warnings)} warning(s)" if warnings else ""

    if errors:
        print(f"\n{REPO_NAME}: {len(errors)} problem(s){warn_note} "
              f"in {len(notes)} file(s)", file=sys.stderr)
        return 1
    if not args.quiet:
        vocab_note = "" if vocabulary is None else f", {len(vocabulary)} tags allowed"
        print(f"{REPO_NAME}: clean ({checked} note(s) checked{vocab_note}{warn_note})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
