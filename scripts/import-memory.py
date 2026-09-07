#!/usr/bin/env python3
"""Import Copilot memory notes into a repo's inbox/, one note per file.

    ../base/scripts/import-memory.py <dir-or-file>... [--repo PATH] [--tag TAG] [--dry-run]

One copy, in kb-base. The target repo is the git work tree this is run in, or
--repo. Input is what `export-copilot-sessions.py --source memory` produces:
Markdown files Copilot wrote with its memory tool, laid out as
<Project>/repo/<name>.md or <Project>/session-<uuid8>/<name>.md.

A memory note is already a distillation, so nothing is clipped or restructured.
The first `#` heading becomes the title (else the file name); the rest is the
body, appended below frontmatter that newnote.sh writes. Everything else
follows import-copilot.py, whose redact() and prose_safe() this imports rather
than copies:

  * Filed RAW and never sent to any API; tagged `import, needs-review`.
  * `created:`/`updated:` are the file's modified date — the last time Copilot
    believed the note. The import date is the `source:` field.
  * Secrets are redacted or the note is refused; the output is re-scanned.
  * Dedupe, two ways: `origin: copilot-memory/<Project>/<rel>` in any existing
    note means this file was imported before; an existing note with the same
    title means a human already brought it in by hand. Both skip.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from lint import collect_notes, find_repo_root, find_secrets, slugify, split_frontmatter  # noqa: E402

# redact() and prose_safe() live in import-copilot.py; import the sibling rather
# than copy them. Its top level only defines constants, so importing is inert.
_spec = importlib.util.spec_from_file_location("import_copilot", BASE / "scripts" / "import-copilot.py")
_ic = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ic)
redact, prose_safe = _ic.redact, _ic.prose_safe

REPO_ROOT = Path(".")
BASE_TAGS = ["import", "needs-review"]
INDEX_NAMES = {"memory-notes-index.md", "raw-transcripts-index.md", "tool-outputs-index.md"}


def origin_of(path: Path) -> str:
    """<Project>/<rel> — relative to the nearest 'memory-notes' ancestor, else the
    two last directories, so the same file gives the same origin from anywhere."""
    parts = path.resolve().parts
    if "memory-notes" in parts:
        rel = Path(*parts[parts.index("memory-notes") + 1:])
    else:
        rel = Path(*parts[-3:])
    return f"copilot-memory/{rel.as_posix()}"


def norm(title: str) -> str:
    return " ".join(title.split()).casefold()


def existing() -> tuple[set[str], set[str]]:
    origins, titles = set(), set()
    for p in collect_notes(REPO_ROOT):
        try:
            fields, err = split_frontmatter(p.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError):
            continue
        if err:
            continue
        if fields.get("origin"):
            origins.add(fields["origin"].strip())
        if fields.get("title"):
            titles.add(norm(fields["title"]))
    return origins, titles


def parse_note(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    title, body_start = "", 0
    for i, l in enumerate(lines):
        if l.startswith("#"):
            title = l.lstrip("#").strip().strip("*").strip()
            body_start = i + 1
            break
    if not title:
        title = path.stem.replace("-", " ").replace("_", " ").strip() or path.stem
    title = " ".join(title.split())[:80]
    body = "\n".join(lines[body_start:]).strip("\n")
    when = dt.date.fromtimestamp(path.stat().st_mtime).isoformat()
    origin = origin_of(path)
    project = origin.split("/")[1] if origin.count("/") >= 2 else "unknown"
    return dict(title=title, body=body, when=when, origin=origin, project=project, file=path.name)


def render(n: dict) -> tuple[list[str], int]:
    meta = [f"**Source:** Copilot memory tool — {n['project']}",
            f"**Origin:** {n['origin']}",
            f"**File date:** {n['when']}", "",
            "> Copilot-authored memory note, imported verbatim and never sent to any API.",
            "> Verify before trusting; supersede or delete once distilled.", ""]
    lines = meta + n["body"].split("\n")
    lines, redactions = redact(lines)
    return prose_safe(lines), redactions


def survivors(lines: list[str]) -> list[str]:
    return sorted({label for label, _ in find_secrets("\n".join(lines))})


def write_note(n: dict, lines: list[str], tags: str, dry_run: bool) -> Path:
    base = f"inbox/{n['when']}-{slugify(n['title'], n['origin'].split('/')[-1][:20])}"
    rel, k = base, 2
    while (REPO_ROOT / f"{rel}.md").exists():
        rel, k = f"{base}-{k}", k + 1
    target = REPO_ROOT / f"{rel}.md"
    if dry_run:
        return target
    subprocess.run([str(BASE / "scripts" / "newnote.sh"),
                    "--tags", tags, "--created", n["when"], "--updated", n["when"],
                    "--field", f"source: copilot-memory-{dt.date.today().isoformat()}",
                    "--field", f"origin: {n['origin']}",
                    rel, n["title"], "note"],
                   check=True, capture_output=True, text=True, cwd=REPO_ROOT)
    with target.open("a", encoding="utf-8") as fh:
        fh.write("\n" + "\n".join(lines).rstrip() + "\n")
    return target


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", type=Path, help="memory .md files or directories of them")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo", type=Path, help="target repo root (default: the git work tree you run this in)")
    ap.add_argument("--tag", action="append", default=[], help="extra tag(s), must be in tags.txt")
    args = ap.parse_args()

    global REPO_ROOT
    REPO_ROOT = args.repo.resolve() if args.repo else find_repo_root()
    if not (REPO_ROOT / "AGENTS.md").exists() or not (REPO_ROOT / ".git").exists():
        print(f"not a vault repo: {REPO_ROOT}", file=sys.stderr); return 1
    vocab = {l.strip() for l in (BASE / "tags.txt").read_text().splitlines() if l.strip() and not l.startswith("#")}
    bad = [t for t in args.tag if t not in vocab]
    if bad:
        print(f"tag(s) not in tags.txt: {', '.join(bad)}", file=sys.stderr); return 1
    tags = BASE_TAGS + [t for t in args.tag if t not in BASE_TAGS]
    if len(tags) > 5:
        print(f"too many tags ({len(tags)}); lint allows 5", file=sys.stderr); return 1
    tag_str = ", ".join(tags)

    files = sorted({f for p in args.paths for f in ([p] if p.is_file() else p.rglob("*.md"))
                    if f.name not in INDEX_NAMES})
    if not files:
        print("no .md memory notes found", file=sys.stderr); return 1
    origins, titles = existing()
    (REPO_ROOT / "inbox").mkdir(parents=True, exist_ok=True)
    planned = by_origin = by_title = refused = 0

    for f in files:
        n = parse_note(f)
        if n["origin"] in origins:
            print(f"  skip (already imported): {n['origin']}"); by_origin += 1; continue
        if norm(n["title"]) in titles:
            print(f"  skip (a note with this title exists): {n['file']} — {n['title'][:50]}"); by_title += 1; continue
        lines, redactions = render(n)
        if survivors(lines):
            print(f"  {'WOULD REFUSE' if args.dry_run else 'REFUSED'} {n['file']}: survived redaction — {', '.join(survivors(lines))}")
            refused += 1; continue
        target = write_note(n, lines, tag_str, args.dry_run)
        origins.add(n["origin"]); titles.add(norm(n["title"])); planned += 1
        flag = f"  redacted={redactions}" if redactions else ""
        print(f"  {'[dry-run] ' if args.dry_run else ''}{n['origin'].split('/',1)[1]} -> {target.relative_to(REPO_ROOT)}{flag}")

    print(f"\n{planned} {'planned' if args.dry_run else 'written'}, {by_origin} already imported, "
          f"{by_title} already in the vault by title, {refused} refused")
    if not args.dry_run and planned:
        lint = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "lint.py"), "--quiet"],
                              capture_output=True, text=True, cwd=REPO_ROOT)
        print(lint.stderr.strip() or "lint: clean")
        return lint.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
