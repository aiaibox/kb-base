#!/usr/bin/env python3
"""Export Claude Code sessions to the plain-text format import-copilot.py reads.

    ../base/scripts/export-claude-sessions.py --out DIR [--skip-existing DIR ...] [--only SID8,...]
                              [--min-turns 1] [--dry-run]

Reads ~/.claude/projects/<encoded-cwd>/<session>.jsonl — one JSONL per session,
one record per event. Only these records carry conversation:
  user       message.content: str, or blocks {text | document | tool_result}
  assistant  message.content blocks {text | thinking | tool_use}; message.model
  system     subtype compact_boundary — context was compacted here
  ai-title / custom-title — the session's title (custom wins)
Everything else (attachment, queue-operation, last-prompt, file-history-*,
frame-link, atis-latch, artifact-*) is harness bookkeeping and is skipped.

Output mirrors the Copilot exports so the same importer applies:
  <out>/<Project>/<YYYY-MM-DD>_<sid8>_<slug>.txt   date = last user turn, UTC
  banner between 80-char '=' rules, `# TURN n   <UTC ts>Z   model=<m>` headers,
  exact `----- USER -----` / `----- ASSISTANT -----` delimiters.
A turn is one human message plus everything the assistant did until the next
one. Recorded: `[thinking] ...`, `[tool: <name>] <compact input>` (values cut to
200 chars, line to 600), `[tool-result] ...` — the result text when it is short
(<= 300 chars), else `[tool-result: N chars]` and `error` when flagged —
`[attachment: <name>, N chars]` for pasted documents, and `[compact-summary] ...`
where Claude Code compacted the context. Harness-injected <system-reminder>
and <local-command-*> spans inside user text are removed; a bare
"[Request interrupted by user]" is kept, it is an event. A body line that
itself looks like a delimiter, rule or TURN header is prefixed with a
backslash so it cannot mis-split the importer; stray control bytes are dropped.

Also copied, verbatim: per-project memory/ notes (Claude's own notes) to
<out>/memory-notes/<Project>/, out-of-line tool-results/ to
<out>/tool-outputs/<Project>/<sid>/, and ~/.claude/file-history/<sid>/ (the
snapshots Claude Code keeps of files it edited) to <out>/file-history/.

Project = basename of the session's cwd; cwds outside ~/code get the parent as
prefix (private-<name>). A session whose transcript is still being written
(the one running this) exports up to its current end.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, re, shutil, sys
from pathlib import Path

HOME = Path.home()
CLAUDE = HOME / ".claude"
UTC = dt.timezone.utc
RULE_EQ, RULE_HASH = "=" * 80, "#" * 78
NOISE = re.compile(r"<system-reminder>.*?</system-reminder>|<local-command-caveat>.*?</local-command-caveat>|"
                   r"<command-name>.*?</command-name>|<command-message>.*?</command-message>|"
                   r"<command-args>.*?</command-args>|<local-command-stdout>.*?</local-command-stdout>|"
                   r"<ide_opened_file>.*?</ide_opened_file>|<ide_selection>.*?</ide_selection>", re.S)


def project_name(cwd: str) -> str:
    p = Path(cwd) if cwd else None
    if not p:
        return "unknown"
    if p.parent == HOME / "code" or p == HOME or p.parent == HOME:
        return p.name
    return f"{p.parent.name}-{p.name}"


def slug(title: str, n: int = 40) -> str:
    s = re.sub(r"[^A-Za-z0-9_]+", "-", title.replace(".", "")).strip("-")
    return s[:n].rstrip("-") or "session"


def ts(v, fallback):
    try:
        return dt.datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(UTC)
    except Exception:
        return fallback


def compact(v, per=200, total=600) -> str:
    if isinstance(v, dict):
        cut = {k: (x[:per] + "…" if isinstance(x, str) and len(x) > per else x) for k, x in v.items()}
        s = json.dumps(cut, ensure_ascii=False, separators=(", ", ": "))
    else:
        s = str(v)
    return s if len(s) <= total else s[:total] + "…"


STRUCTURAL = re.compile(r"^(----- (?:USER|ASSISTANT) -----|#{4,}|={4,}|# TURN \d.*)$")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def body_safe(text: str) -> str:
    """A body line that looks like one of this format's structural lines would
    mis-split the importer (a session that discusses the export format prints
    them); prefix it with a backslash. Stray control bytes make tools treat the
    file as binary; drop them."""
    out = []
    for line in CONTROL.sub("", text).split("\n"):
        out.append("\\" + line if STRUCTURAL.match(line) else line)
    return "\n".join(out)


def clean_user(text: str) -> str:
    return NOISE.sub("", text).strip()


def result_text(block) -> str:
    c = block.get("content")
    if isinstance(c, list):
        c = "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    c = (c or "").strip()
    err = " error" if block.get("is_error") else ""
    if len(c) <= 300:
        return f"[tool-result{err}] {c}".rstrip() if c else f"[tool-result{err}: empty]"
    return f"[tool-result{err}: {len(c):,} chars] {c.splitlines()[0][:120]}"


def load(path: Path) -> dict | None:
    turns, cur = [], None
    title_ai = title_custom = ""
    cwd = ""; entry = set(); models = []; compactions = 0; docs = 0
    last = dt.datetime.fromtimestamp(path.stat().st_mtime, UTC)

    def ensure(t):
        nonlocal cur
        if cur is None:
            cur = dict(ts=t, model="", user="", lines=[])
            turns.append(cur)
        return cur

    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            o = json.loads(ln)
        except json.JSONDecodeError:
            continue
        t = o.get("type")
        cwd = cwd or o.get("cwd", "")
        if o.get("entrypoint"):
            entry.add(o["entrypoint"])
        now = ts(o.get("timestamp"), last); last = now if o.get("timestamp") else last
        if t == "ai-title":
            title_ai = o.get("aiTitle") or title_ai
        elif t == "custom-title":
            title_custom = o.get("customTitle") or title_custom
        elif t == "system" and o.get("subtype") == "compact_boundary":
            compactions += 1
            ensure(now)["lines"].append("[compact-boundary] context was compacted here")
        elif t == "user":
            m = o.get("message") or {}; c = m.get("content")
            if o.get("isCompactSummary"):
                txt = c if isinstance(c, str) else " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
                ensure(now)["lines"].append("[compact-summary] " + txt.strip())
                continue
            if isinstance(c, str):
                text = clean_user(c)
                if text:
                    cur = dict(ts=now, model="", user=text, lines=[]); turns.append(cur)
                continue
            if not isinstance(c, list):
                continue
            texts, results, attach = [], [], []
            for b in c:
                if not isinstance(b, dict):
                    continue
                bt = b.get("type")
                if bt == "text":
                    x = clean_user(b.get("text", ""))
                    if x:
                        texts.append(x)
                elif bt == "tool_result":
                    results.append(result_text(b))
                elif bt == "document":
                    src = b.get("source") or {}; data = src.get("data") or ""
                    docs += 1
                    attach.append(f"[attachment: {b.get('title') or src.get('media_type') or 'document'}, {len(data):,} chars]")
            if results:
                ensure(now)["lines"].extend(results)
            if texts or attach:
                cur = dict(ts=now, model="", user="\n".join(texts + attach), lines=[]); turns.append(cur)
        elif t == "assistant":
            m = o.get("message") or {}; c = m.get("content")
            mdl = m.get("model") or ""
            turn = ensure(now)
            if mdl and not mdl.startswith("<"):
                turn["model"] = turn["model"] or mdl
                if mdl not in models:
                    models.append(mdl)
            if isinstance(c, str):
                if c.strip():
                    turn["lines"].append(c.rstrip())
                continue
            for b in c or []:
                if not isinstance(b, dict):
                    continue
                bt = b.get("type")
                if bt == "text" and b.get("text", "").strip():
                    turn["lines"].append(b["text"].rstrip())
                elif bt == "thinking" and b.get("thinking", "").strip():
                    turn["lines"].append("[thinking] " + b["thinking"].strip())
                elif bt == "tool_use":
                    turn["lines"].append(f"[tool: {b.get('name', 'tool')}] {compact(b.get('input'))}".rstrip())
    for tn in turns:
        tn["assistant"] = "\n".join(tn.pop("lines"))
    turns = [tn for tn in turns if tn["user"].strip() or tn["assistant"].strip()]
    if not turns:
        return None
    first = next((tn["user"] for tn in turns if tn["user"].strip()), "")
    fallback = next((l.strip() for l in first.splitlines() if l.strip() and not l.startswith(("[", "<", "==="))), "")
    title = (title_custom or title_ai or fallback)[:80]
    return dict(sid=path.stem, project=project_name(cwd), cwd=cwd, title=title, turns=turns, models=models or ["unrecorded"],
                created=turns[0]["ts"], updated=last, entry=",".join(sorted(entry)) or "?", compactions=compactions, docs=docs,
                src=str(path).replace(str(HOME), "~"))


def write(s: dict, out: Path, dry_run: bool) -> dict:
    user_ts = [t["ts"] for t in s["turns"] if t["user"].strip()] or [t["ts"] for t in s["turns"]]
    name = f"{max(user_ts).date().isoformat()}_{s['sid'][:8]}_{slug(s['title'])}.txt"
    target = out / s["project"] / name
    note = [f"exported from the Claude Code transcript ({s['src']}); entrypoint={s['entry']}.",
            "Thinking, tool calls with compact inputs, and short tool results are recorded;",
            "long tool results are summarised as [tool-result: N chars]. Harness-injected",
            "reminders are removed from user text."]
    if s["compactions"]:
        note.append(f"Context was compacted {s['compactions']} time(s); each point is marked and the summary kept.")
    if s["docs"]:
        note.append(f"{s['docs']} pasted document(s) are noted by name and size, not reproduced.")
    lines = [RULE_EQ, f"SESSION {s['sid']}", f"Project : {s['project']}"]
    if s["title"]:
        lines.append(f"Title   : {s['title']}")
    lines += [f"Created : {s['created'].date().isoformat()}   Updated: {s['updated'].date().isoformat()}   Turns: {len(s['turns'])}",
              f"Models  : {', '.join(s['models'])}", "Source  : Claude Code session log (~/.claude/projects, full)"]
    lines += [("Note    : " if i == 0 else "          ") + l for i, l in enumerate(note)]
    lines += [RULE_EQ, ""]
    for n, t in enumerate(s["turns"], 1):
        lines += [RULE_HASH, f"# TURN {n}   {t['ts'].strftime('%Y-%m-%d %H:%M:%SZ')}   model={t['model'] or 'unrecorded'}", RULE_HASH, "",
                  "----- USER -----", body_safe(t["user"].rstrip("\n")), "", "----- ASSISTANT -----", body_safe(t["assistant"].rstrip("\n")), "", ""]
    text = "\n".join(lines).rstrip("\n") + "\n"
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return dict(sid=s["sid"], project=s["project"], title=s["title"], turns=len(s["turns"]), updated=s["updated"].date().isoformat(),
                size=len(text.encode()), rel=f"{s['project']}/{name}", compactions=s["compactions"], entry=s["entry"])


def existing_ids(dirs) -> set[str]:
    seen = set()
    for d in dirs:
        for p in Path(d).expanduser().rglob("*.txt"):
            m = re.search(r"^SESSION ([0-9a-f-]{36})", p.read_text(errors="replace")[:2000], re.M)
            if m:
                seen.add(m.group(1))
    return seen


def copy_side(out: Path, projects: dict, dry_run: bool) -> dict:
    n = {"memory": 0, "tool-outputs": 0, "file-history": 0}
    for pdir in (CLAUDE / "projects").glob("*/"):
        proj = projects.get(pdir.name)
        if not proj:
            continue
        for p in (pdir / "memory").glob("*.md"):
            n["memory"] += 1
            if not dry_run:
                (out / "memory-notes" / proj).mkdir(parents=True, exist_ok=True); shutil.copy2(p, out / "memory-notes" / proj / p.name)
        for p in pdir.glob("*/tool-results/*"):
            n["tool-outputs"] += 1
            if not dry_run:
                d = out / "tool-outputs" / proj / p.parent.parent.name[:8]; d.mkdir(parents=True, exist_ok=True); shutil.copy2(p, d / p.name)
    for sdir in (CLAUDE / "file-history").glob("*/"):
        proj = next((projects[k] for k in projects if (CLAUDE / "projects" / k / f"{sdir.name}.jsonl").exists()), None)
        for p in sdir.rglob("*"):
            if p.is_file():
                n["file-history"] += 1
                if not dry_run:
                    d = out / "file-history" / (proj or "unknown") / sdir.name[:8] / p.relative_to(sdir).parent; d.mkdir(parents=True, exist_ok=True); shutil.copy2(p, d / p.name)
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--skip-existing", nargs="*", default=[])
    ap.add_argument("--only")
    ap.add_argument("--min-turns", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    skip = existing_ids(a.skip_existing)
    only = [x.lower() for x in a.only.split(",")] if a.only else None
    done, empty, skipped, projects = [], 0, 0, {}
    for path in sorted((CLAUDE / "projects").glob("*/*.jsonl")):
        if only and not any(path.stem.startswith(o) for o in only):
            continue
        if path.stem in skip:
            skipped += 1; continue
        try:
            s = load(path)
        except Exception as e:
            print(f"  ERROR {path.stem[:8]}: {type(e).__name__}: {e}", file=sys.stderr); continue
        if not s or len(s["turns"]) < a.min_turns:
            empty += 1; continue
        projects[path.parent.name] = s["project"]
        r = write(s, a.out, a.dry_run); done.append(r)
        print(f"  {'[dry-run] ' if a.dry_run else ''}{r['rel']}  turns={r['turns']} {r['size']/1024:.0f}KB"
              + (f" compactions={r['compactions']}" if r['compactions'] else "") + f" via {r['entry']}")
    side = copy_side(a.out, projects, a.dry_run)
    print(f"\n{len(done)} {'planned' if a.dry_run else 'written'}, {skipped} already exported, {empty} empty; "
          f"memory notes {side['memory']}, tool-output files {side['tool-outputs']}, file-history files {side['file-history']}")
    if done and not a.dry_run:
        by = {}
        for r in done:
            by.setdefault(r["project"], []).append(r)
        idx = [f"# Claude Code sessions — {a.out.name}", "", f"_Generated {dt.date.today().isoformat()} from `~/.claude/projects/*/*.jsonl`._", "",
               f"**{len(done)} sessions** across **{len(by)} projects**, one `.txt` each, grouped by project. Same format as the Copilot exports; import with `import-copilot.py`.",
               "Thinking, tool calls (compact inputs) and short tool results recorded; long results summarised; pasted documents noted by size.",
               f"Also here: `memory-notes/` ({side['memory']} Claude-authored notes — import with `import-memory.py`), `tool-outputs/` ({side['tool-outputs']} out-of-line results), `file-history/` ({side['file-history']} snapshots of edited files). Exclude those folders when importing sessions.", ""]
        for proj in sorted(by):
            rs = sorted(by[proj], key=lambda r: r["updated"], reverse=True)
            idx += [f"## {proj} — {len(rs)} sessions, {sum(r['turns'] for r in rs)} turns", "", "| Updated | Turns | Size | File | Title |", "|---------|------:|-----:|------|-------|"]
            idx += [f"| {r['updated']} | {r['turns']} | {r['size']/1024/1024:.1f} MB | `{r['rel']}` | {r['title'] or '(untitled)'} |" for r in rs]
            idx.append("")
        (a.out / "raw-transcripts-index.md").write_text("\n".join(idx), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
