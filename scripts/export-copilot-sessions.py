#!/usr/bin/env python3
"""Export VS Code Copilot chat history to the ~/vscode-chat plain-text format.

    ../base/scripts/export-copilot-sessions.py --out DIR
        [--source chatSessions|transcripts|memory|resources|all]
        [--skip-existing DIR ...] [--include-known] [--min-turns 1]
        [--only UUID8,...] [--dry-run]

One copy, in kb-base. Everything GitHub Copilot Chat leaves on this Mac, under
~/Library/Application Support/Code/User/, exported to plain files that
import-copilot.py / import-memory.py can read. Four sources:

  chatSessions  workspaceStorage/*/chatSessions/<uuid>.json | .jsonl
                VS Code's own store. .json is a full session object; .jsonl is a
                snapshot on line 1 then deltas (kind 1 = set at path k, kind 2 =
                append to the array at k). .jsonl wins when both exist.
  transcripts   workspaceStorage/*/GitHub.copilot-chat/transcripts/<uuid>.jsonl
                The Copilot Chat extension's own event log (producer
                copilot-agent): session.start, user.message, assistant.message
                {content, reasoningText}, tool.execution_start {toolName,
                arguments}, tool.execution_complete {success}. It survives when
                a session is deleted from VS Code's history, so by default this
                source exports only uuids that have NO chatSessions file
                (--include-known overrides). It records no model ids and no tool
                results.
  memory        workspaceStorage/*/GitHub.copilot-chat/memory-tool/memories/**/*.md
                and globalStorage/github.copilot-chat/memory-tool/. Copilot-authored
                notes, already Markdown: copied verbatim to <out>/memory-notes/
                <Project>/..., per-session dirs renamed session-<uuid8>, with an
                index that marks notes whose heading or stem already appears in
                the vault (private/ is never read for this).
  resources     workspaceStorage/*/GitHub.copilot-chat/chat-session-resources/:
                the raw tool-call payloads (terminal output, file reads) VS Code
                keeps out-of-line — the material every transcript omits. Copied
                to <out>/tool-outputs/<Project>/<session-uuid>/<call>/content.txt.

`all` runs the four in turn. Output is identical in shape for both sources and matches the original 50-file
export byte-for-byte in structure:
  <out>/<Project>/<YYYY-MM-DD>_<uuid8>_<slug>.txt   date = last user turn, UTC
  slug = title with '.' removed, other non-[A-Za-z0-9_] runs -> '-', cut to 40,
  trailing '-' stripped; 'session' when the title is empty.
Banner between 80-char '=' rules; each turn framed by 78-char '#' rules and a
`# TURN n   <UTC ts>Z   model=<m>` header; exact `----- USER -----` /
`----- ASSISTANT -----` delimiters; `[thinking] ...` and `[tool: <name>] ...`
lines. For transcripts, tool ARGUMENTS are recorded (each value cut to 200
chars, line to 600) and a failed call is marked `-> FAILED`. Edits, undo stops,
code-block URIs and tool-result payloads are never present in either source.

--skip-existing DIR: uuids found in `SESSION <uuid>` lines of .txt files under
DIR are not exported again. Project = workspace folder basename; workspaces
outside ~/code get their parent as prefix (e.g. private-<name>) so same-named
projects stay distinguishable.
"""
from __future__ import annotations
import argparse, copy, datetime as dt, json, os, re, sys
from pathlib import Path

HOME = Path.home()
STORE = HOME / "Library/Application Support/Code/User/workspaceStorage"
UTC = dt.timezone.utc
RULE_EQ, RULE_HASH = "=" * 80, "#" * 78
SKIP_KINDS = {"textEditGroup", "undoStop", "codeblockUri", "mcpServersStarting",
              "prepareToolInvocation", "progressTaskSerialized", "workspaceEdit",
              "progressMessage", "codeCitations", "confirmation", "questionCarousel"}

# ----------------------------------------------------------------- shared ---

def workspace_folder(hs: Path) -> str:
    try:
        w = json.loads((hs / "workspace.json").read_text())
        return (w.get("folder") or w.get("workspace") or "").replace("file://", "").replace("%20", " ")
    except Exception:
        return ""


def project_name(folder: str) -> str:
    if not folder:
        return "unknown"
    p = Path(folder)
    if p.parent == HOME / "code" or p == HOME or p.parent == HOME:
        return p.name
    return f"{p.parent.name}-{p.name}"


def slug(title: str, n: int = 40) -> str:
    s = re.sub(r"[^A-Za-z0-9_]+", "-", title.replace(".", "")).strip("-")
    return s[:n].rstrip("-") or "session"


def text_of(x):
    if isinstance(x, dict):
        return x.get("value") or ""
    if isinstance(x, list):
        return "\n".join(text_of(i) for i in x)
    return str(x or "")


def parse_ts(v, fallback: dt.datetime) -> dt.datetime:
    try:
        if isinstance(v, (int, float)):
            return dt.datetime.fromtimestamp(v / 1000, UTC)
        if isinstance(v, str) and v:
            return dt.datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(UTC)
    except Exception:
        pass
    return fallback


def write_export(sid, project, title, created, updated, models, turns, out_dir: Path,
                 source_line, note_lines, dry_run):
    """turns: [{'ts': datetime, 'model': str, 'user': str, 'assistant': str}]"""
    user_ts = [t["ts"] for t in turns if t["user"]] or [t["ts"] for t in turns]
    name = f"{max(user_ts).date().isoformat()}_{sid[:8]}_{slug(title)}.txt"
    target = out_dir / project / name
    lines = [RULE_EQ, f"SESSION {sid}", f"Project : {project}"]
    if title:
        lines.append(f"Title   : {title}")
    lines += [f"Created : {created.date().isoformat()}   Updated: {updated.date().isoformat()}   Turns: {len(turns)}",
              f"Models  : {', '.join(models)}", f"Source  : {source_line}"]
    lines += [("Note    : " if i == 0 else "          ") + ln for i, ln in enumerate(note_lines)]
    lines += [RULE_EQ, ""]
    for n, t in enumerate(turns, 1):
        lines += [RULE_HASH, f"# TURN {n}   {t['ts'].strftime('%Y-%m-%d %H:%M:%SZ')}   model={t['model']}", RULE_HASH, "",
                  "----- USER -----", t["user"].rstrip("\n"), "", "----- ASSISTANT -----", t["assistant"].rstrip("\n"), "", ""]
    text = "\n".join(lines).rstrip("\n") + "\n"
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return dict(sid=sid, project=project, title=title, turns=len(turns), updated=updated.date().isoformat(),
                size=len(text.encode("utf-8")), rel=f"{project}/{name}")


def existing_ids(dirs) -> set[str]:
    seen = set()
    for d in dirs:
        for p in Path(d).expanduser().rglob("*.txt"):
            try:
                m = re.search(r"^SESSION ([0-9a-f-]{36})", p.read_text(errors="replace")[:2000], re.M)
            except OSError:
                continue
            if m:
                seen.add(m.group(1))
    return seen

# ----------------------------------------------------------- chatSessions ---

def apply(root, k, v, kind):
    cur = root
    for i, key in enumerate(k[:-1]):
        nxt_idx = isinstance(k[i + 1], int)
        if isinstance(cur, list):
            while len(cur) <= key:
                cur.append(None)
            if cur[key] is None:
                cur[key] = [] if nxt_idx else {}
            cur = cur[key]
        else:
            cur = cur.setdefault(key, [] if nxt_idx else {})
    last = k[-1]
    if kind == 1:
        if isinstance(cur, list):
            while len(cur) <= last:
                cur.append(None)
            cur[last] = v
        else:
            cur[last] = v
    elif kind == 2:
        if isinstance(cur, list):
            while len(cur) <= last:
                cur.append(None)
            if cur[last] is None:
                cur[last] = []
            tgt = cur[last]
        else:
            tgt = cur.setdefault(last, [])
        tgt.extend(v) if isinstance(v, list) else tgt.append(v)
    else:
        raise ValueError(f"unknown delta kind {kind}")


def load_chat_session(path: Path) -> dict:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    first = json.loads(lines[0])
    root = copy.deepcopy(first["v"] if first.get("kind") == 0 else first)
    for ln in lines[1:]:
        if ln.strip():
            o = json.loads(ln)
            apply(root, o["k"], o.get("v"), o["kind"])
    return root


def render_response(parts) -> str:
    out: list[str] = []
    for part in parts or []:
        if not isinstance(part, dict):
            continue
        kind = part.get("kind")
        if kind is None and "value" in part:
            t = text_of(part["value"]).rstrip("\n")
            if t:
                out.append(t)
        elif kind == "thinking":
            t = text_of(part.get("value")).strip("\n")
            if t:
                out.append("[thinking] " + t)
        elif kind == "toolInvocationSerialized":
            tool = part.get("toolId") or (part.get("toolSpecificData") or {}).get("kind") or "tool"
            msg = text_of(part.get("invocationMessage")) or text_of(part.get("pastTenseMessage"))
            out.append(f"[tool: {tool}] {msg}".rstrip())
        elif kind == "inlineReference":
            name = part.get("name") or ""
            if not name:
                ref = part.get("inlineReference")
                name = os.path.basename((ref.get("fsPath") or ref.get("path") or "") if isinstance(ref, dict) else str(ref or ""))
            if name:
                out[-1] = out[-1] + f"`{name}`" if out else f"`{name}`"
    return "\n".join(out)


def iter_chat_sessions():
    for hs in STORE.glob("*/"):
        folder = workspace_folder(hs)
        files: dict[str, Path] = {}
        for p in list(hs.glob("chatSessions/*.json")) + list(hs.glob("chatSessions/*.jsonl")):
            sid = p.name.split(".")[0]
            if sid not in files or p.suffix == ".jsonl":
                files[sid] = p
        for sid, p in files.items():
            yield sid, p, folder


def export_chat_session(sid, path, folder, out_dir, dry_run):
    s = load_chat_session(path)
    reqs = [r for r in (s.get("requests") or []) if isinstance(r, dict) and (r.get("message") or {}).get("text")]
    if not reqs:
        return None
    now = dt.datetime.now(UTC)
    ts_last = max(r.get("timestamp") or 0 for r in reqs)
    turns = [dict(ts=parse_ts(r.get("timestamp") or ts_last, now), model=r.get("modelId") or "unknown",
                  user=r["message"]["text"] or "", assistant=render_response(r.get("response"))) for r in reqs]
    models: list[str] = []
    for t in turns:
        if t["model"] not in models:
            models.append(t["model"])
    r = write_export(sid, project_name(folder), (s.get("customTitle") or "").strip(),
                     parse_ts(s.get("creationDate") or ts_last, now), parse_ts(ts_last, now), models, turns, out_dir,
                     "VS Code Copilot chatSessions log (full, untruncated)",
                     ["raw tool-result payloads (file/terminal dumps) omitted; user prompts,",
                      "assistant answers, reasoning, and tool actions are complete."], dry_run)
    r["fmt"] = path.suffix[1:]
    return r

# ------------------------------------------------------------ transcripts ---

def compact_args(args, per=200, total=600) -> str:
    if not isinstance(args, dict):
        return str(args or "")[:total]
    cut = {k: (v[:per] + "…" if isinstance(v, str) and len(v) > per else v) for k, v in args.items()}
    s = json.dumps(cut, ensure_ascii=False, separators=(", ", ": "))
    return s if len(s) <= total else s[:total] + "…}"


def iter_transcripts():
    for hs in STORE.glob("*/"):
        folder = workspace_folder(hs)
        for p in hs.glob("GitHub.copilot-chat/transcripts/*.jsonl"):
            yield p.name.split(".")[0], p, folder


def export_transcript(sid, path, folder, out_dir, dry_run):
    mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, UTC)
    events = []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.strip():
            try:
                events.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    if not events:
        return None
    created = None
    turns: list[dict] = []
    cur = None
    calls: dict[str, tuple[dict, int]] = {}
    tools_seen: set[str] = set()
    last_ts = mtime
    agent_only = False
    for ev in events:
        t, d = ev.get("type"), ev.get("data") or {}
        ts = parse_ts(ev.get("timestamp"), last_ts)
        last_ts = ts
        if t == "session.start":
            created = parse_ts(d.get("startTime"), ts)
            continue
        if t == "user.message":
            cur = dict(ts=ts, model="unrecorded", user=(d.get("content") or ""), lines=[])
            for a in d.get("attachments") or []:
                nm = a.get("name") or a.get("fileName") or a.get("uri") or a.get("path") if isinstance(a, dict) else str(a)
                if nm:
                    cur["user"] += f"\n[attachment] {nm}"
            turns.append(cur)
            continue
        if cur is None:
            # events before the first logged user message: the log began mid-turn
            cur = dict(ts=ts, model="unrecorded", user="", lines=[])
            turns.append(cur)
        if t == "assistant.message":
            r, c = (d.get("reasoningText") or "").strip("\n"), (d.get("content") or "").rstrip("\n")
            if r.strip():
                cur["lines"].append("[thinking] " + r)
            if c.strip():
                cur["lines"].append(c)
        elif t == "tool.execution_start":
            name = d.get("toolName") or "tool"
            tools_seen.add(name)
            cur["lines"].append(f"[tool: {name}] {compact_args(d.get('arguments'))}".rstrip())
            calls[d.get("toolCallId")] = (cur, len(cur["lines"]) - 1)
        elif t == "tool.execution_complete":
            hit = calls.get(d.get("toolCallId"))
            if hit and d.get("success") is False:
                c2, i = hit
                c2["lines"][i] += "  -> FAILED"
    for t in turns:
        t["assistant"] = "\n".join(t.pop("lines"))
    turns = [t for t in turns if t["user"].strip() or t["assistant"].strip()]
    if not turns:
        return None
    first_user = next((t["user"] for t in turns if t["user"].strip()), "")
    agent_only = not first_user
    leading = bool(turns) and not turns[0]["user"].strip() and not agent_only
    title = next((l.strip() for l in first_user.splitlines() if l.strip()), "")[:80]
    note = ["absent from VS Code's chatSessions store; recovered from the Copilot Chat",
            "extension's event log. Title is the first user line. Tool ARGUMENTS are",
            "recorded (values cut to 200 chars); tool results and model ids are not",
            "recorded by the source."]
    if agent_only:
        note.append("Agent-initiated run: no user message was recorded at all.")
    elif leading:
        note.append("The log begins mid-conversation: turn 1 is assistant work that preceded")
        note.append("the first logged user message, so it has an empty USER section.")
    r = write_export(sid, project_name(folder), title, created or turns[0]["ts"], last_ts, ["unrecorded"], turns,
                     out_dir, "VS Code Copilot Chat extension transcript log (GitHub.copilot-chat/transcripts)", note, dry_run)
    r.update(fmt="transcript", agent_only=agent_only, leading=leading, tools=len(tools_seen))
    return r

# --------------------------------------------------- memory + resources ---

VAULT = Path(__file__).resolve().parents[2]          # <vault>/base/scripts/this


def vault_index() -> tuple[set[str], set[str]]:
    """(titles, origins) from the frontmatter of every note outside private/ and
    base/ — the same two keys import-memory.py dedupes on. A memory note's file
    name showing up inside some transcript's body is NOT 'already in the vault':
    the session that wrote the memory merely logged its path."""
    from lint import split_frontmatter
    titles, origins = set(), set()
    for p in VAULT.glob("*/**/*.md"):
        rel = p.relative_to(VAULT).parts
        if rel[0] in ("private", "base") or ".git" in rel:
            continue
        try:
            fields, err = split_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if err:
            continue
        if fields.get("title"):
            titles.add(" ".join(fields["title"].split()).casefold())
        if fields.get("origin"):
            origins.add(fields["origin"].strip())
    return titles, origins


def export_memory(out: Path, dry_run: bool) -> int:
    import base64, shutil
    root = STORE.parent / "globalStorage"
    files = list(root.glob("*opilot-chat/memory-tool/**/*.md"))
    files += list(STORE.glob("*/GitHub.copilot-chat/memory-tool/**/*.md"))
    titles, origins = vault_index()
    rows = []
    for p in sorted(files):
        scope = "global" if "/globalStorage/" in str(p) else project_name(workspace_folder(Path(str(p).split("/GitHub.copilot-chat/")[0])))
        parts = str(p).split("memory-tool/memories/")[1].split("/")
        if len(parts) > 1 and parts[0] != "repo":
            try:
                parts[0] = "session-" + base64.b64decode(parts[0]).decode()[:8]
            except Exception:
                pass
        rel = "/".join(parts)
        text = p.read_text(encoding="utf-8", errors="replace")
        h1 = next((l.lstrip("# ").strip() for l in text.splitlines() if l.startswith("#")), "")
        in_vault = (" ".join(h1.split()).casefold() in titles) or (f"copilot-memory/{scope}/{rel}" in origins)
        dst = out / "memory-notes" / scope / rel
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
        rows.append((scope, rel, p.stat().st_size, dt.date.fromtimestamp(p.stat().st_mtime).isoformat(), h1, in_vault))
        print(f"  {'[dry-run] ' if dry_run else ''}memory-notes/{scope}/{rel}  {p.stat().st_size/1024:.1f}KB{'  (already in vault)' if in_vault else ''}")
    if rows and not dry_run:
        idx = ["# Copilot memory notes — copied from VS Code's memory tool", "",
               f"_Copied {dt.date.today().isoformat()} from `GitHub.copilot-chat/memory-tool/memories/` (global + per workspace). Copilot-authored notes, not transcripts; already Markdown. Import with `import-memory.py`._", "",
               f"**{len(rows)} files, {sum(r[2] for r in rows)/1024:.0f} KB.** {sum(1 for r in rows if r[5])} already imported into the vault (a note with the same title or `origin:` exists; marked ✓). Per-session dirs are renamed `session-<uuid8>`.", "",
               "| In vault | Scope | File | Size | Updated | Heading |", "|:-:|---|---|---:|---|---|"]
        idx += [f"| {'✓' if iv else ''} | {s} | `{r}` | {z/1024:.1f} KB | {m} | {h[:70]} |" for s, r, z, m, h, iv in sorted(rows, key=lambda r: (r[5], r[0], r[1]))]
        (out / "memory-notes" / "memory-notes-index.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    print(f"\nmemory: {len(rows)} notes {'planned' if dry_run else 'copied'}, {sum(1 for r in rows if r[5])} already in the vault")
    return len(rows)


def export_resources(out: Path, dry_run: bool) -> int:
    import shutil
    rows = []
    for p in sorted(STORE.glob("*/GitHub.copilot-chat/chat-session-resources/**/*")):
        if not p.is_file():
            continue
        proj = project_name(workspace_folder(Path(str(p).split("/GitHub.copilot-chat/")[0])))
        rel = str(p).split("chat-session-resources/")[1]
        dst = out / "tool-outputs" / proj / rel
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
        rows.append((proj, rel, p.stat().st_size, dt.date.fromtimestamp(p.stat().st_mtime).isoformat()))
    if rows and not dry_run:
        idx = ["# Tool-call payloads — copied from chat-session-resources", "",
               f"_Copied {dt.date.today().isoformat()} from `GitHub.copilot-chat/chat-session-resources/` per workspace. Raw tool-call payloads (terminal output, file reads) that VS Code stores out-of-line — the material the transcript exports omit. Path: `<project>/<session-uuid>/call_<toolCallId>__vscode-<ts>/content.txt`._", "",
               f"**{len(rows)} files, {sum(r[2] for r in rows)/1024:.0f} KB.** Not session logs: exclude this folder when importing.", "",
               "| Project | File | Size | Date |", "|---|---|---:|---|"]
        idx += [f"| {pj} | `{r}` | {z/1024:.1f} KB | {d} |" for pj, r, z, d in rows]
        (out / "tool-outputs" / "tool-outputs-index.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    print(f"resources: {len(rows)} payload files {'planned' if dry_run else 'copied'}")
    return len(rows)

# ------------------------------------------------------------------- main ---

def write_index(out: Path, done: list[dict], source: str, extra: list[str]):
    by: dict[str, list[dict]] = {}
    for r in done:
        by.setdefault(r["project"], []).append(r)
    idx = [f"# Raw Chat Transcripts — {out.name}", "",
           f"_Generated {dt.date.today().isoformat()} from {source}._", "",
           f"**{len(done)} sessions** across **{len(by)} projects**, one `.txt` each, grouped by project."] + extra + [
           "Full untruncated user prompts + assistant answers + `[thinking]`/`[tool:]` lines.",
           "Raw tool-result payloads (file/terminal dumps) are omitted.", ""]
    for proj in sorted(by):
        rs = sorted(by[proj], key=lambda r: r["updated"], reverse=True)
        idx += [f"## {proj} — {len(rs)} sessions, {sum(r['turns'] for r in rs)} turns", "",
                "| Updated | Turns | Size | File | Title |", "|---------|------:|-----:|------|-------|"]
        idx += [f"| {r['updated']} | {r['turns']} | {r['size']/1024/1024:.1f} MB | `{r['rel']}` | {r['title'] or '(untitled)'}{' _(agent-initiated, no user message)_' if r.get('agent_only') else ''} |" for r in rs]
        idx.append("")
    (out / "raw-transcripts-index.md").write_text("\n".join(idx), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--source", choices=["chatSessions", "transcripts", "memory", "resources", "all"], default="chatSessions")
    ap.add_argument("--skip-existing", nargs="*", default=[])
    ap.add_argument("--include-known", action="store_true", help="transcripts: also export uuids that have a chatSessions file")
    ap.add_argument("--min-turns", type=int, default=1)
    ap.add_argument("--only")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.source in ("memory", "resources", "all"):
        if a.source in ("memory", "all"):
            export_memory(a.out, a.dry_run)
        if a.source in ("resources", "all"):
            export_resources(a.out, a.dry_run)
        if a.source != "all":
            return 0
        print()
    skip = existing_ids(a.skip_existing)
    only = [x.strip().lower() for x in a.only.split(",")] if a.only else None
    known = {sid for sid, _, _ in iter_chat_sessions()}
    done, n_skip, n_empty, n_known = [], 0, 0, 0
    jobs = []
    if a.source in ("chatSessions", "all"):
        jobs += [(export_chat_session, sid, p, f) for sid, p, f in iter_chat_sessions()]
    if a.source in ("transcripts", "all"):
        for sid, p, f in iter_transcripts():
            if sid in known and not a.include_known:
                n_known += 1
                continue
            jobs.append((export_transcript, sid, p, f))
    for fn, sid, p, f in sorted(jobs, key=lambda j: (j[3], j[1])):
        if only and not any(sid.startswith(o) for o in only):
            continue
        if sid in skip:
            n_skip += 1
            continue
        try:
            r = fn(sid, p, f, a.out, a.dry_run)
        except Exception as e:
            print(f"  ERROR {sid[:8]} {p.name}: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        if r is None or r["turns"] < a.min_turns:
            n_empty += 1
            continue
        done.append(r)
        flag = (" agent-only" if r.get("agent_only") else "") + (" leading-partial-turn" if r.get("leading") else "") + (f" tools={r['tools']}" if r.get("tools") else "")
        print(f"  {'[dry-run] ' if a.dry_run else ''}{r['rel']}  turns={r['turns']} {r['fmt']} {r['size']/1024:.0f}KB{flag}")
    print(f"\n{len(done)} {'planned' if a.dry_run else 'written'}, {n_skip} already exported, {n_empty} empty/below --min-turns"
          + (f", {n_known} transcripts skipped (have a chatSessions file)" if a.source != "chatSessions" else ""))
    if done and not a.dry_run:
        src = {"chatSessions": "VS Code Copilot `chatSessions/*.json` and `*.jsonl` logs",
               "transcripts": "the Copilot Chat extension's `GitHub.copilot-chat/transcripts/*.jsonl` event logs — sessions with NO chatSessions file",
               "all": "both the chatSessions store and the extension transcript logs"}[a.source]
        extra = ["Sessions already present under: " + (", ".join(f"`{d}`" for d in a.skip_existing) or "(none)") + " were skipped."]
        if a.source != "chatSessions":
            extra.append(f"{n_known} transcripts belonging to sessions that do have a chatSessions file were skipped; {n_empty} were empty.")
        write_index(a.out, done, src, extra)
    return 0


if __name__ == "__main__":
    sys.exit(main())
