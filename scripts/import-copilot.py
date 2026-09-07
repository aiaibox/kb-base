#!/usr/bin/env python3
"""Import VS Code Copilot chat sessions into a repo's inbox/, one note per session.

    ../base/scripts/import-copilot.py <dir-or-file>... [--repo PATH]
                                      [--tag project] [--dry-run] [--budget 48000]

One copy, in kb-base. The target repo is the git work tree this is run in — the
same rule as lint and newnote — or --repo. The target's own lint.py runs at the
end so the pre-commit contract is its own.

Input is the plain-text chatSessions log exported on the MacBook Pro: a banner
(SESSION <uuid>, Project, Title, Created/Updated/Turns, Models) between rules
of `=`, then turns introduced by `# TURN n <ts> model=<m>` and delimited by
exactly `----- USER -----` / `----- ASSISTANT -----`. Bodies contain their own
`---` and `#`, so only those two lines, whole and anchored, are delimiters.

Decisions, 2026-09-06:
  * Everything is filed RAW, tagged `import, needs-review`, and NOTHING is sent
    to any API. This is employer material; the vault's own filter would hold
    back two thirds of it anyway. Distil locally, then delete the transcript.
  * `created:`/`updated:` are the SESSION's dates so inbox/ sorts by when the
    work happened. The import date is the `source:` field.
  * Secrets are redacted, never filed: private-key blocks removed whole, every
    other lint SECRET_PATTERNS hit replaced with <redacted:label>. `<` is
    outside the inline-credential value class, so the replacement cannot
    itself match. The output is re-scanned and the note refused if anything
    survives.
  * Bodies over --budget are clipped at TURN granularity — head ¼, tail ¾, the
    conclusion is at the end — with the omission stated and the source path
    and uuid kept so the rest stays reachable.
  * Dedupe on the session uuid: a `**Session:** <uuid>` line anywhere in this
    repo means already imported.

Reuses lint's SECRET_PATTERNS and watcher's slugify rather than copying them,
and creates every note through newnote.sh so ids are real.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent   # kb-base: lint, newnote, tags, templates
sys.path.insert(0, str(BASE / "scripts"))
from lint import (collect_notes, find_repo_root, slugify, clip, raw_transcript,  # noqa: E402
                  redact, prose_safe, survivors, resolve_tags)

REPO_ROOT = Path(".")                            # set in main(): --repo, else the work tree run in
INBOX = REPO_ROOT / "inbox"

RULE_EQ = re.compile(r"^=+$")
RULE_HASH = re.compile(r"^#+$")
# Timestamp is "YYYY-MM-DD HH:MM:SSZ" — date and time separated by a SPACE in the
# real logs (a T in some tooling), so it cannot be captured as one \S+ token.
TURN_HDR = re.compile(r"^# TURN (\d+)\s+(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}Z?)\s+model=(\S+)")
USER, ASSISTANT = "----- USER -----", "----- ASSISTANT -----"
UUID_RE = re.compile(r"^SESSION ([0-9a-f-]{36})\s*$", re.M)
DATE = r"(\d{4}-\d{2}-\d{2})"
SESSION_LINE = re.compile(r"^\*\*Session:\*\* ([0-9a-f-]{36})", re.M)
BASE_TAGS = ["import", "needs-review"]
TAGS = ", ".join(BASE_TAGS)                      # extended by --tag in main()


def parse_session(text: str, path: Path) -> dict | None:
    lines = text.split("\n")
    rules = [i for i, l in enumerate(lines[:40]) if RULE_EQ.match(l.strip())]
    if len(rules) < 2:
        return None
    banner = "\n".join(lines[rules[0] + 1:rules[1]])
    m = UUID_RE.search(banner)
    if not m:
        return None
    field = lambda k: (re.search(rf"^{k}\s*:\s*(.*)$", banner, re.M) or [None, ""])[1].strip()  # noqa: E731
    created = (re.search(rf"Created\s*:\s*{DATE}", banner) or [None, ""])[1]
    updated = (re.search(rf"Updated\s*:\s*{DATE}", banner) or [None, created])[1]

    turns: list[dict] = []
    cur: dict | None = None
    role: str | None = None
    buf: list[str] = []

    def flush():
        nonlocal buf
        if cur is not None and role:
            cur[role] = "\n".join(buf).strip()
        buf = []

    for line in lines[rules[1] + 1:]:
        h = TURN_HDR.match(line)
        if h:
            flush(); role = None
            cur = {"n": int(h.group(1)), "ts": h.group(2), "model": h.group(3), "user": "", "assistant": ""}
            turns.append(cur); continue
        if RULE_HASH.match(line.strip()):
            continue
        if line == USER:
            flush(); role = "user"; continue
        if line == ASSISTANT:
            flush(); role = "assistant"; continue
        if role:
            buf.append(line)
    flush()
    turns = [t for t in turns if t["user"] or t["assistant"]]
    if not turns or not any(t["assistant"].strip() for t in turns):
        return None            # a pasted log with no answer is not a note; three such were deleted at triage

    title, fallback = field("Title"), False
    if not title:
        fallback = True
        first = next((l.strip() for l in turns[0]["user"].splitlines() if l.strip()), "")
        title = first[:60] or path.stem
    title = re.sub(r"\s+", " ", title)[:80]

    return {"uuid": m.group(1), "project": field("Project") or path.parent.name,
            "title": title, "title_fallback": fallback, "created": created,
            "updated": updated or created, "models": field("Models"),
            "turns": turns, "file": f"{path.parent.parent.name}/{path.parent.name}/{path.name}"}


def clip_turns(turns: list[dict], budget: int):
    """Head ¼ + tail ¾ at turn granularity. Returns (kept_head, kept_tail, omitted)."""
    size = lambda t: len(t["user"]) + len(t["assistant"])  # noqa: E731
    if sum(map(size, turns)) <= budget:
        return turns, [], []
    head, used = [], 0
    for t in turns:
        if used + size(t) > budget // 4:
            break
        head.append(t); used += size(t)
    tail, used = [], 0
    for t in reversed(turns):
        if t in head or used + size(t) > budget - budget // 4:
            break
        tail.insert(0, t); used += size(t)
    if not head:
        head = [turns[0]]
    if not tail and turns[-1] not in head:
        tail = [turns[-1]]
    omitted = [t for t in turns if t not in head and t not in tail]
    return head, tail, omitted


def clip_text(text: str, limit: int) -> str:
    """One turn body, via watcher.clip. Turn-granular clipping keeps the first
    and last turn whole, and a 2 MB pasted log in either would otherwise pass."""
    return clip(text, limit)[0]


def render(s: dict, budget: int) -> tuple[list[str], int, str]:
    head, tail, omitted = clip_turns(s["turns"], budget)
    shortened = 0

    def turn(t):
        nonlocal shortened
        u, a = clip_text(t["user"], budget // 2), clip_text(t["assistant"], budget // 2)
        shortened += (u != t["user"]) + (a != t["assistant"])
        return [{"role": "User", "suffix": f"turn {t['n']} · {t['ts']} · {t['model']}", "text": u},
                {"role": "Assistant", "text": a}]

    turns: list = [x for t in head for x in turn(t)]
    if omitted:
        turns.append(f"*[… {len(omitted)} turn(s) omitted …]*")
    turns += [x for t in tail for x in turn(t)]

    clip_note = ""
    if omitted:
        chars = sum(len(t["user"]) + len(t["assistant"]) for t in omitted)
        clip_note = (f"kept turns {head[0]['n']}–{head[-1]['n']} and {tail[0]['n']}–{tail[-1]['n']}; "
                     f"omitted {len(omitted)} turn(s), {chars:,} chars")
    if shortened:
        note = f"{shortened} oversized turn body(ies) shortened in place"
        clip_note = f"{clip_note}; {note}" if clip_note else note

    meta = [f"**Source:** VS Code Copilot — {s['project']}",
            f"**Session:** {s['uuid']}",
            f"**File:** {s['file']}",
            f"**Created:** {s['created']} · **Updated:** {s['updated']} · **Turns:** {len(s['turns'])}",
            f"**Models:** {s['models'] or 'unrecorded'}"]
    remarks = ["Imported raw — never sent to any API. Distil locally, then delete the",
               "transcript below."]
    if clip_note:
        remarks.append(f"Clipped: {clip_note}. The full session is at **File:** above.")

    lines = "\n".join(raw_transcript(meta, remarks, turns)).split("\n")
    lines, redactions = redact(lines)
    return prose_safe(lines, close_before=("### User — turn ",)), redactions, clip_note

def already_imported() -> set[str]:
    seen: set[str] = set()
    for p in collect_notes(REPO_ROOT):
        try:
            seen.update(SESSION_LINE.findall(p.read_text(encoding="utf-8")))
        except (UnicodeDecodeError, OSError):
            pass
    return seen


def write_note(s: dict, lines: list[str], dry_run: bool) -> Path | None:
    base = f"inbox/{s['created']}-{slugify(s['title'], s['uuid'][:8])}"
    rel, k = base, 2
    while (REPO_ROOT / f"{rel}.md").exists():
        rel, k = f"{base}-{k}", k + 1
    target = REPO_ROOT / f"{rel}.md"
    if dry_run:
        return target
    if survivors(lines):
        raise SystemExit(f"{s['file']}: {', '.join(survivors(lines))} survived redaction; refusing to write")
    subprocess.run([str(BASE / "scripts" / "newnote.sh"),
                    "--tags", TAGS, "--created", s["created"], "--updated", max(s["updated"], s["created"]),
                    "--field", f"source: copilot-vscode-{dt.date.today().isoformat()}",
                    rel, s["title"], "note"],
                   check=True, capture_output=True, text=True, cwd=REPO_ROOT)
    with target.open("a", encoding="utf-8") as fh:
        fh.write("\n" + "\n".join(lines).rstrip() + "\n")
    return target

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", type=Path, help="session .txt files or directories of them")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=int, default=48_000, help="max body chars before turn-level clipping")
    ap.add_argument("--repo", type=Path, help="target repo root (default: the git work tree you run this in)")
    ap.add_argument("--tag", action="append", default=[], help="extra tag(s), must be in the target's tags.txt")
    args = ap.parse_args()

    global REPO_ROOT, INBOX, TAGS
    REPO_ROOT = args.repo.resolve() if args.repo else find_repo_root()
    INBOX = REPO_ROOT / "inbox"
    if not (REPO_ROOT / "AGENTS.md").exists() or not (REPO_ROOT / ".git").exists():
        print(f"not a vault repo: {REPO_ROOT}", file=sys.stderr); return 1
    TAGS = resolve_tags(BASE_TAGS, args.tag)

    files = sorted({f for p in args.paths for f in ([p] if p.is_file() else p.rglob("*.txt"))})
    if not files:
        print("no .txt sessions found", file=sys.stderr); return 1
    seen = already_imported()
    INBOX.mkdir(parents=True, exist_ok=True)
    planned = dupes = fallbacks = clipped = unparsed = 0

    for f in files:
        s = parse_session(f.read_text(encoding="utf-8", errors="replace"), f)
        if s is None:
            print(f"  skip (not a session log): {f.name}"); unparsed += 1; continue
        if s["uuid"] in seen:
            print(f"  skip (already imported {s['uuid'][:8]}): {f.name}"); dupes += 1; continue
        lines, redactions, clip_note = render(s, args.budget)
        if args.dry_run and survivors(lines):
            # A dry run must show the refusal too, or it is not a rehearsal of the run.
            print(f"  WOULD REFUSE {f.name}: survived redaction — {', '.join(survivors(lines))}"); continue
        target = write_note(s, lines, args.dry_run)
        seen.add(s["uuid"]); planned += 1
        fallbacks += s["title_fallback"]; clipped += bool(clip_note)
        flag = "".join([" title-fallback" if s["title_fallback"] else "",
                        f" redacted={redactions}" if redactions else "",
                        " clipped" if clip_note else ""])
        print(f"  {'[dry-run] ' if args.dry_run else ''}{f.name} -> {target.relative_to(REPO_ROOT)}  turns={len(s['turns'])}{flag}")

    print(f"\n{planned} {'planned' if args.dry_run else 'written'}, {dupes} already imported, "
          f"{fallbacks} title fallback(s), {clipped} clipped, {unparsed} unparsed")
    if not args.dry_run and planned:
        lint = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "lint.py"), "--quiet"],
                              capture_output=True, text=True, cwd=REPO_ROOT)
        print(lint.stderr.strip() or f"lint: clean")
        return lint.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
