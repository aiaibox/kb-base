#!/usr/bin/env python3
"""Weekly triage digest across all four repos.

    ../base/scripts/review.py [--all] [--stale-days N]

Answers one question: what needs a human this week? Everything it reports is
something no automated rule can settle — a capture that needs filing, a note
flagged for a decision, a price that has probably drifted.

Vault-wide: it walks every sibling repo of kb-base and runs each one's own
lint.py for pass/fail rather than reimplementing any check.

`private` is reported by COUNT AND PATH ONLY, never by title. Its filenames are
numeric because git-crypt encrypts contents but not names, so a path leaks
nothing; a title would. This keeps the digest safe to paste anywhere.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

KB = Path(__file__).resolve().parent.parent.parent
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from lint import (split_frontmatter, parse_tags, DOC_FILES,  # noqa: E402
                  collect_notes)

# Every sibling that is a git repo. Derived, so adding a repo needs no edit here.
REPOS = sorted(p.name for p in KB.iterdir() if (p / ".git").exists())
OPAQUE = {"private"}            # report without titles
STATE_FILE = KB / ".review-state.json"
INBOX_MAX_DAYS = 30             # RULES.md: nothing in inbox older than this
STALE_DAYS = 90                 # a volatile note unreviewed this long is suspect
TODO_TAGS = ["needs-review", "promote-to-public", "superseded"]

TICK, CROSS, DOT = "ok", "->", " ·"


def notes(repo: Path):
    """Every real note in a repo: lint's definition, minus the root docs."""
    for p in collect_notes(repo):
        if p.name in DOC_FILES and p.parent == repo:
            continue
        yield p, p.relative_to(repo)


def read(p: Path):
    """Frontmatter fields, or None if unreadable (git-crypt locked, binary)."""
    try:
        text = p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None
    fields, err = split_frontmatter(text)
    return None if err else fields


def age(datestr: str) -> int | None:
    try:
        return (dt.date.today() - dt.date.fromisoformat(datestr.strip())).days
    except (ValueError, AttributeError):
        return None


def scan(stale_days: int) -> dict:
    out = {}
    for name in REPOS:
        repo = KB / name
        if not repo.is_dir():
            continue
        r = {"total": 0, "unreadable": 0, "volatile": 0, "all": [],
             "inbox": [], "stale_volatile": [],
             "todo": {t: [] for t in TODO_TAGS}, "opaque": name in OPAQUE}
        for p, rel in notes(repo):
            r["total"] += 1
            f = read(p)
            if f is None:
                r["unreadable"] += 1
                continue
            tags = parse_tags(f.get("tags", ""))
            title = f.get("title", "").strip().strip('"') or rel.stem
            item = {"path": str(rel), "title": title,
                    "updated": f.get("updated", ""),
                    "suggested": f.get("suggested_folder", "").strip()}
            r["all"].append(item)
            if rel.parts[0] == "inbox":
                # Inbox age is time since ARRIVAL. Imported notes carry their
                # content date in created:, so prefer the import date that the
                # importers append to source: (…-YYYY-MM-DD).
                src = f.get("source", "").strip()
                item["age"] = age(src[-10:]) if age(src[-10:]) is not None else age(f.get("created", ""))
                r["inbox"].append(item)
            for t in TODO_TAGS:
                if t in tags:
                    r["todo"][t].append(item)
            if "volatile" in tags:
                r["volatile"] += 1
                a = age(f.get("updated", ""))
                if a is not None and a >= stale_days:
                    r["stale_volatile"].append({**item, "age": a})
        r["stale_volatile"].sort(key=lambda i: -i["age"])
        r["inbox"].sort(key=lambda i: -(i["age"] or 0))
        out[name] = r
    return out


def label(repo: str, item: dict) -> str:
    """Path always; title only where it is safe to print."""
    return item["path"] if repo in OPAQUE else f"{item['path']}  {item['title']}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="list every item instead of the first 10 per section")
    ap.add_argument("--stale-days", type=int, default=STALE_DAYS,
                    help=f"volatile notes unreviewed this long (default {STALE_DAYS})")
    ap.add_argument("--notify", action="store_true",
                    help="post a macOS notification with the headline count "
                         "(used by the weekly launchd agent)")
    args = ap.parse_args()
    cap = None if args.all else 10

    data = scan(args.stale_days)
    prev = {}
    if STATE_FILE.exists():
        try:
            prev = json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            prev = {}
    last_run = prev.get("date", "never")

    print(f"\nKB review — {dt.date.today().isoformat()}   (last run: {last_run})")
    print("=" * 68)

    # --- Totals and growth -------------------------------------------------
    print("\nNotes")
    before = prev.get("totals", {})
    for name, r in data.items():
        d = r["total"] - before.get(name, r["total"])
        delta = f"{d:+d}" if d else "  ="
        opaque = "  (titles suppressed)" if r["opaque"] else ""
        unread = f"  {r['unreadable']} unreadable — git-crypt locked?" \
            if r["unreadable"] else ""
        print(f"  {name:<9} {r['total']:>4}  {delta}{opaque}{unread}")

    # --- Inbox -------------------------------------------------------------
    print("\nInbox — target state is empty")
    any_inbox = False
    for name, r in data.items():
        if not r["inbox"]:
            continue
        any_inbox = True
        over = [i for i in r["inbox"] if (i["age"] or 0) > INBOX_MAX_DAYS]
        flag = f"  {CROSS} {len(over)} past {INBOX_MAX_DAYS} days" if over else ""
        print(f"  {name}: {len(r['inbox'])}{flag}")
        for i in r["inbox"][:cap]:
            a = f"{i['age']}d" if i["age"] is not None else "  ?"
            hint = f"   suggests: {i['suggested']}" if i["suggested"] else ""
            print(f"    {a:>5}{DOT} {label(name, i)}{hint}")
        if cap and len(r["inbox"]) > cap:
            print(f"          … {len(r['inbox']) - cap} more (--all)")
    if not any_inbox:
        print(f"  {TICK} all four empty")

    # --- Flagged for a decision -------------------------------------------
    for tag in TODO_TAGS:
        rows = [(n, i) for n, r in data.items() for i in r["todo"][tag]]
        if not rows:
            continue
        print(f"\n{tag} — {len(rows)}")
        for n, i in rows[:cap]:
            print(f"  {n:<9}{DOT} {label(n, i)}")
        if cap and len(rows) > cap:
            print(f"          … {len(rows) - cap} more (--all)")

    # --- Volatile decay ----------------------------------------------------
    rows = [(n, i) for n, r in data.items() for i in r["stale_volatile"]]
    rows.sort(key=lambda t: -t[1]["age"])
    pool = sum(r["volatile"] for r in data.values())
    print(f"\nVolatile — {pool} tracked, {len(rows)} unreviewed "
          f"{args.stale_days}+ days")
    if rows:
        print("  Prices, fees, quotas and policies drift. Re-verify or mark superseded.")
        for n, i in rows[:cap]:
            print(f"  {i['age']:>4}d{DOT} {n:<9} {label(n, i)}")
        if cap and len(rows) > cap:
            print(f"          … {len(rows) - cap} more (--all)")
    else:
        print(f"  {TICK} none due yet. These decay by nature — prices, fees, "
              f"quotas, policies")

    # --- Merge candidates ------------------------------------------------
    # RULES.md §7: merge first. Pairs of notes in one repo whose titles share
    # three or more significant words are the cheapest signal that two notes
    # answer one question. Listed, never acted on — merging is a judgement.
    STOP = set("the and for with from that this into your when which where what how not but are was were "
               "been have has had can could should would will may might over under than then them they "
               "their about after before onto only also more less most very just like same".split())
    pairs = []
    for name, r in data.items():
        if r["opaque"]:
            continue
        words = [(i, {w for w in re.findall(r"[a-z0-9]{4,}", i["title"].lower()) if w not in STOP})
                 for i in r["all"]]
        for x in range(len(words)):
            for y in range(x + 1, len(words)):
                shared = words[x][1] & words[y][1]
                if len(shared) >= 3:
                    pairs.append((len(shared), name, words[x][0], words[y][0]))
    pairs.sort(key=lambda t: -t[0])
    print(f"\nMerge candidates — {len(pairs)} pair(s) sharing 3+ title words")
    for n, name, a, b in pairs[:cap or len(pairs)]:
        print(f"  [{n}] {name}{DOT} {a['path']}\n      {DOT} {b['path']}")
    if cap and len(pairs) > cap:
        print(f"          … {len(pairs) - cap} more (--all)")

    # --- Machine checks ----------------------------------------------------
    print("\nChecks")
    for name in data:
        p = subprocess.run([sys.executable, str(KB / name / "scripts" / "lint.py")], cwd=KB / name,
                           capture_output=True, text=True)
        tail = ((p.stdout + p.stderr).strip().splitlines() or ["no output"])[-1]
        print(f"  lint {name:<9} {TICK if p.returncode == 0 else CROSS}  {tail}")
    for name in data:
        r = subprocess.run(["git", "-C", str(KB / name), "status", "--porcelain"],
                           capture_output=True, text=True)
        n = len([l for l in r.stdout.splitlines() if l.strip()])
        ahead = subprocess.run(
            ["git", "-C", str(KB / name), "rev-list", "--count", "@{u}..HEAD"],
            capture_output=True, text=True).stdout.strip() or "?"
        if n or ahead not in ("0", "?"):
            print(f"  git  {name:<9} {CROSS}  {n} uncommitted, {ahead} unpushed")

    # --- What to do --------------------------------------------------------
    todo = []
    inbox_total = sum(len(r["inbox"]) for r in data.values())
    if inbox_total:
        todo.append(f"File {inbox_total} inbox note(s) — the suggestion is a "
                    f"starting point, not a decision")
    nr = sum(len(r["todo"]["needs-review"]) for r in data.values())
    if nr:
        todo.append(f"Resolve {nr} needs-review — most are duplicate flags that "
                    f"need a merge-or-keep call")
    pp = sum(len(r["todo"]["promote-to-public"]) for r in data.values())
    if pp:
        todo.append(f"Restate {pp} note(s) into public/ — a restatement, never a move")
    if rows:
        todo.append(f"Re-verify the {min(3, len(rows))} stalest volatile note(s)")
    if pairs:
        todo.append(f"Consider merging {len(pairs)} title-overlap pair(s) — RULES.md §7, merge first")
    print("\nThis week" if todo else f"\n{TICK} Nothing needs a human this week")
    for i, t in enumerate(todo, 1):
        print(f"  {i}. {t}")
    print()

    if args.notify:
        # The digest itself goes to the log; this is only the nudge that makes
        # someone open it. Silence when there is nothing to do, so the
        # notification keeps meaning something.
        if todo:
            body = todo[0] if len(todo) == 1 else \
                f"{len(todo)} things need a human. {todo[0]}"
            subprocess.run(["osascript", "-e",
                            f'display notification {json.dumps(body)} '
                            f'with title "KB weekly review"'],
                           capture_output=True)

    STATE_FILE.write_text(json.dumps(
        {"date": dt.date.today().isoformat(),
         "totals": {n: r["total"] for n, r in data.items()}}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
