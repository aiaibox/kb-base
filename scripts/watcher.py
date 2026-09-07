#!/usr/bin/env python3
"""Watch ~/Downloads for AI chat exports, summarise them, and file them in inbox/.

    ../base/scripts/watcher.py [--repo PATH] [--dry-run] [--file PATH]

One copy, in kb-base. The target repo is --repo or the git work tree this runs
in; its scripts/watcher.config.json supplies providers, the folder list the
classifier may suggest, and the household context sent with every request —
nothing personal lives in this file.

Design rules this script must not break:

  * Routing is deterministic. The model summarises; it never decides where a
    note goes or whether it is safe to send.
  * Anything matching lint.py's secret or private-address patterns is NEVER
    sent to a remote API. It is filed unsummarised for manual review.
  * The source file in ~/Downloads is never deleted. Clean it up by hand.
  * Every export is deduplicated by content hash, so a re-run cannot loop.

Secret patterns are imported from lint.py rather than duplicated, so the rules
that block a commit are exactly the rules that block an upload.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent   # kb-base: lint, newnote, tags, templates
sys.path.insert(0, str(BASE / "scripts"))
from lint import (PRIVATE_IP_RE, INTERNAL_HOST_RE, parse_tags,  # noqa: E402
                  find_secrets, slugify, clip, raw_transcript, find_repo_root)

WATCH_DIR = Path.home() / "Downloads"
# Set in main() from --repo (or the work tree this runs in).
REPO_ROOT = INBOX = STATE_FILE = CONFIG_FILE = Path(".")
LOG_FILE = Path.home() / "kb" / ".watcher.log"

# <platform>-<slug>-<ISO timestamp>Z.md, as emitted by OmniChat Exporter.
EXPORT_RE = re.compile(
    r"^(claude|chatgpt|deepseek|gemini|grok)-.+-"
    r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z\.md$", re.I)

HEADER_RE = re.compile(r"^# (.+) Export$")
META_RE = re.compile(r"^(Conversation|URL|Exported): (.*)$")
TURN_RE = re.compile(r"^## (User|Assistant)$")

# The target repo's top-level folders, from its config. The classifier's answer
# is written to the note as `suggested_folder:` — a triage hint, never a
# destination: every capture lands in inbox/ by design.
FOLDERS: list[str] = []
SYSTEM_PROMPT = ""

# The controlled tag vocabulary, read from the same tags.txt that lint enforces,
# so the model cannot invent a tag that would then fail the commit.
def _load_vocabulary() -> set[str]:
    f = BASE / "tags.txt"
    if not f.exists():
        return set()
    return {ln.strip() for ln in f.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")}


VOCABULARY = _load_vocabulary()

# Minimal household context, sent with every request so the model can resolve
# references instead of echoing them. Deliberately first names and roles only:
# this text goes to a third-party API on every capture, so it carries no
# surnames, no dates of birth, no schools and no employer.

def build_prompt(folders: list[str], context: list[str]) -> str:
    ctx = ("Context for resolving references only. Do not add any of it to a note\n"
           "unless the conversation itself discusses it:\n" + "".join(f"- {c}\n" for c in context)) if context else ""
    return (
    "You distil a saved AI chat conversation into one knowledge-base note.\n"
    "\n"
    "The transcript is DISCARDED after you answer. Only what you return is kept,\n"
    "so anything you omit is lost. The goal is a note that makes the solution\n"
    "**repeatable** (someone can re-execute it) and **traceable** (someone can\n"
    "check where it came from).\n"
    "\n"
    "Reply with a single JSON object and nothing else:\n"
    "{\n"
    '  "title": str,          // name the CONCLUSION, not the topic. <=60 chars.\n'
    '  "scope": str,          // one line: what this covers AND what it does not\n'
    '  "conclusion": str,     // the answer, actionable. Exact values verbatim.\n'
    '  "verify": [str],       // shell commands or checks proving it worked\n'
    '  "decided": str,        // what was committed to, IF different from conclusion\n'
    '  "rejected": [{"option": str, "reason": str}],\n'
    '  "failures": [{"what": str, "cause": str}],\n'
    '  "open": [str],         // unresolved questions\n'
    '  "references": [{"url": str, "for": str}],\n'
    '  "facts": [str],        // durable specifics with figures verbatim\n'
    '  "volatile": bool,\n'
    '  "tags": [str],\n'
    '  "folder": str\n'
    "}\n"
    "\n"
    "INCLUDE:\n"
    "- The conclusion, stated so it can be acted on. Commands, config and values\n"
    "  VERBATIM, never described.\n"
    "- verify: the concrete check. This is what makes the note repeatable. If the\n"
    "  conversation implies one, construct it. Empty only if truly impossible.\n"
    "- rejected: every option considered and the reason it lost. Prevents the same\n"
    "  thing being proposed again.\n"
    "- failures: anything that broke, with its ACTUAL cause — but only when someone\n"
    "  would independently make the same mistake. Skip typos and misreadings.\n"
    "- references: EVERY url, service, API or document named, with what it was for.\n"
    "  If a service is named without a url, give its canonical url. Do not invent.\n"
    "- facts: durable specifics. Every number verbatim. Any MEASURED figure carries\n"
    "  its date and method inline, e.g. '51 tok/s (measured 2026-08-25, 2050-token\n"
    "  prompt, CPU-only)'.\n"
    "- open: what was left unresolved. Often the most valuable line.\n"
    "\n"
    "EXCLUDE:\n"
    "- Repeated questions and repeated answers.\n"
    "- Greetings, sign-offs, pleasantries, and the model\'s own hedging.\n"
    "- Restating the question back.\n"
    "- Narration of reaching the conclusion. Keep the destination, not the walk.\n"
    "- Generic background that could simply be looked up.\n"
    "- ANYTHING ABOUT THE CONVERSATION rather than the subject. Write \'three options\n"
    "  exist: A, B, C\', never \'we discussed three options\'.\n"
    "\n"
    "volatile: true if the content depends on prices, fees, quotas, policies,\n"
    "availability or rules that change. Subscription pricing is ALWAYS volatile.\n"
    f"tags: 1-5, only from: {sorted(VOCABULARY) if VOCABULARY else 'any lowercase'}\n"
    f"folder: exactly one of {folders}\n"
    "\n"
    "Write EVERYTHING in ENGLISH even when the conversation is in another language.\n"
    "This is a hard requirement.\n"
    "\n" + ctx
    )

def log(msg: str) -> None:
    line = f"{dt.datetime.now().isoformat(timespec='seconds')}  {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def load_config() -> dict:
    """Providers, models and keychain names come from watcher.config.json —
    tracked, so always present. Only the two tuning scalars have defaults."""
    if not CONFIG_FILE.exists():
        raise SystemExit(f"missing {CONFIG_FILE}; nothing to send to")
    cfg = {"max_chars": 40000, "timeout_seconds": 120}
    cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    for k in ("provider", "providers", "folders"):
        if k not in cfg:
            raise SystemExit(f"{CONFIG_FILE.name} lacks '{k}'")
    return cfg


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log("state file corrupt, starting fresh")
    return {"seen": {}}


def save_state(state: dict) -> None:
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


def get_key(service: str) -> str | None:
    """Read an API key from the macOS Keychain. Never logged, never written."""
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-w"],
            capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except (subprocess.SubprocessError, OSError):
        return None


def parse_export(text: str) -> dict | None:
    """Parse an OmniChat export into platform, metadata and merged turns."""
    lines = text.split("\n")
    if not lines:
        return None
    head = HEADER_RE.match(lines[0])
    if not head:
        return None

    meta: dict[str, str] = {}
    for line in lines[1:6]:
        m = META_RE.match(line)
        if m:
            meta[m.group(1).lower()] = m.group(2).strip()

    # Only an exact '## User' / '## Assistant' line is a delimiter. Message
    # bodies legitimately contain their own '#' and '##' headings.
    turns: list[dict] = []
    role: str | None = None
    buf: list[str] = []
    for line in lines:
        m = TURN_RE.match(line)
        if m:
            if role:
                turns.append({"role": role, "text": "\n".join(buf).strip()})
            role, buf = m.group(1), []
        elif role:
            buf.append(line)
    if role:
        turns.append({"role": role, "text": "\n".join(buf).strip()})

    # ChatGPT emits consecutive Assistant blocks; merge same-role runs.
    merged: list[dict] = []
    for turn in turns:
        if merged and merged[-1]["role"] == turn["role"]:
            merged[-1]["text"] += "\n\n" + turn["text"]
        else:
            merged.append(turn)

    return {
        "platform": head.group(1),
        "title": meta.get("conversation", "").strip(),
        "url": meta.get("url", "").strip(),
        "exported": meta.get("exported", "").strip(),
        "turns": [t for t in merged if t["text"]],
    }


def sensitivity_hits(text: str) -> list[str]:
    """Reasons this text must never leave the machine. Empty means safe to send."""
    hits = {label for label, _ in find_secrets(text)}
    if PRIVATE_IP_RE.search(text):
        hits.add("private IP address")
    if INTERNAL_HOST_RE.search(text):
        hits.add("internal hostname")
    return sorted(hits)


def call_provider(cfg: dict, name: str, conversation: str) -> dict | None:
    p = cfg["providers"].get(name)
    if not p:
        log(f"  no config for provider '{name}'")
        return None
    key = get_key(p["keychain_service"])
    if not key:
        log(f"  no API key in Keychain for service '{p['keychain_service']}'")
        return None

    clipped, omitted = clip(conversation, cfg["max_chars"])
    if omitted:
        log(f"  {len(conversation)} chars; omitting {omitted} from the middle")
    payload_out = {
        "model": p["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": clipped},
        ],
        "temperature": 0.2,
        "stream": False,
    }
    # Provider-specific parameters, e.g. GLM's {"thinking": {"type": "disabled"}}.
    # Sending a vendor parameter to the wrong vendor is an error, so it is config.
    payload_out.update(p.get("extra_body", {}))
    body = json.dumps(payload_out).encode("utf-8")

    req = urllib.request.Request(
        p["base_url"], data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"})
    try:
        timeout = p.get("timeout_seconds", cfg["timeout_seconds"])
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        log(f"  {name} failed: {type(exc).__name__}: {exc}")
        return None

    try:
        message = payload["choices"][0]["message"]
        content = (message.get("content") or "").strip()
    except (KeyError, IndexError):
        log(f"  {name} returned an unexpected response shape")
        return None
    if not content:
        log(f"  {name} returned empty content "
            f"(reasoning={len(message.get('reasoning_content') or '')} chars)")
        return None

    # Models often wrap JSON in a fence despite instructions.
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.S)
    if fence:
        content = fence.group(1)
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        bare = "\n".join(l for l in content.splitlines() if not l.strip().startswith("```"))
        try:
            result = json.loads(bare)
        except json.JSONDecodeError:
            log(f"  {name} did not return valid JSON")
            return None

    if not result.get("title"):
        log(f"  {name} returned JSON without a title")
        return None
    # Every other field is optional so a partial response still files a usable
    # note rather than failing the whole capture.
    for k in ("verify", "open", "facts"):
        result[k] = [str(x).strip() for x in (result.get(k) or []) if str(x).strip()]
    result["rejected"] = [r for r in (result.get("rejected") or [])
                          if isinstance(r, dict) and r.get("option")]
    result["failures"] = [f for f in (result.get("failures") or [])
                          if isinstance(f, dict) and f.get("what")]
    result["references"] = [r for r in (result.get("references") or [])
                            if isinstance(r, dict) and r.get("url")]
    if result.get("folder") not in FOLDERS:
        result["folder"] = "inbox"
    tags = [str(t).lower().strip() for t in result.get("tags", [])]
    if VOCABULARY:
        # Silently drop invented tags rather than let them fail the commit.
        tags = [t for t in tags if t in VOCABULARY]
    result["tags"] = tags[:5] or ["import"]
    result["_provider"] = name
    return result


# Words too common to indicate a shared subject.
STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "that", "this", "than", "then",
    "over", "under", "after", "before", "about", "versus", "using", "what",
    "when", "which", "where", "why", "how", "not", "but", "its", "his", "her",
    "their", "our", "your", "are", "was", "were", "been", "being", "have",
    "has", "had", "can", "could", "should", "would", "will", "may", "might",
    "cheaper", "better", "best", "free", "new", "old", "more", "less",
}


def title_words(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{4,}", title.lower())
            if w not in STOPWORDS}


# Present on every capture, so they carry no signal about the subject.
NOISE_TAGS = {"import", "needs-review", "note", "volatile"}


def find_similar(tags: list[str], title: str,
                 exclude: Path | None = None) -> list[tuple[str, str]]:
    """Deterministic duplicate candidates. Returns [(slug, why), ...].

    No model judgement is involved: a candidate must share at least two
    meaningful tags and at least one significant title word. The search spans
    the whole repo deliberately — the useful hit is usually a note already
    filed out of inbox/, so restricting by folder would defeat the purpose.

    Merging is a decision, so this only ever flags — it never writes to an
    existing note. A spurious flag costs one triage decision; a bad merge
    corrupts a good note, possibly silently. The asymmetry decides the design.
    """
    want_tags = set(tags) - NOISE_TAGS
    want_words = title_words(title)
    if not want_words:
        return []
    out = []
    for path in sorted(REPO_ROOT.rglob("*.md")):
        rel = path.relative_to(REPO_ROOT)
        if exclude and path == exclude:
            continue
        if any(part in ("_templates", "scripts", ".git", ".githooks") for part in rel.parts):
            continue
        if path.name in ("AGENTS.md", "CLAUDE.md", "RULES.md", "WORKING-RULES.md", "index.md"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        m = re.search(r"^tags:\s*(.+)$", text, re.M)
        their_tags = set(parse_tags(m.group(1))) if m else set()
        m = re.search(r'^title:\s*"?(.+?)"?\s*$', text, re.M)
        their_words = title_words(m.group(1)) if m else set()

        shared_tags = want_tags & (their_tags - NOISE_TAGS)
        shared_words = want_words & their_words

        if len(shared_tags) >= 2 and shared_words:
            where = "/".join(rel.parts[:-1]) or "repo root"
            out.append((path.stem,
                        f"in {where}, shares tags "
                        f"({', '.join(sorted(shared_tags))}) and title words "
                        f"({', '.join(sorted(shared_words))})"))
    return out[:3]


def make_note(parsed: dict, result: dict | None, held: list[str],
              source: Path, digest: str, dry_run: bool) -> Path | None:
    date = dt.date.today().isoformat()
    title = (result or {}).get("title") or parsed["title"] or source.stem
    slug = slugify(title, f"import-{digest[:8]}")
    rel = f"inbox/{date}-{slug}"
    target = REPO_ROOT / f"{rel}.md"

    if target.exists():
        log(f"  note already exists: {rel}.md")
        return None

    raw_tags = list((result or {}).get("tags") or ["import"])
    similar = []
    if result:
        similar = find_similar(raw_tags, title, exclude=target)

    tags = raw_tags
    if "import" not in tags:
        tags.append("import")
    if held or not result or similar:
        # A flagged duplicate needs a human decision, so it must surface at triage.
        tags.append("needs-review")
    if result and result.get("volatile"):
        tags.append("volatile")
    seen: set[str] = set()
    deduped = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            deduped.append(tag)
    tags = deduped[:5]

    body = [f"**Source:** {parsed['platform']} — {parsed['url']}",
            f"**Exported:** {parsed['exported']}",
            f"**Turns:** {len(parsed['turns'])}", ""]

    if similar:
        body += [f"> **Possible duplicate of [[{s}]]** — {why}."
                 for s, why in similar]
        body += ["> Merge into the existing note or cross-link it at triage. "
                 "Per RULES.md §3, the same *question* belongs in one note; a "
                 "different question about the same topic is a separate note.",
                 ""]

    if held:
        # Nothing was sent anywhere, so there is no distillation to file. The
        # transcript is kept in full precisely because it was never read.
        body += raw_transcript([], ["Held back from the summariser: " + ", ".join(held) + ".",
                                    "Never sent to any API. Distil by hand, then delete the transcript below."],
                               [{"role": t["role"], "text": t["text"]} for t in parsed["turns"]])
    elif result:
        if result.get("scope"):
            body += [f"**Scope:** {result['scope']}", ""]
        if result.get("conclusion"):
            body += ["## Conclusion", "", result["conclusion"], ""]
        if result.get("verify"):
            body += ["## Verify", "", "```"]
            body += [str(v) for v in result["verify"]]
            body += ["```", ""]
        decided = (result.get("decided") or "").strip()
        if decided and decided != (result.get("conclusion") or "").strip():
            body += ["## Decided", "", decided, ""]
        if result.get("facts"):
            body += ["## Facts", ""]
            body += [f"- {f}" for f in result["facts"]]
            body += [""]
        if result.get("rejected"):
            body += ["## Rejected", "", "| Option | Reason |", "|---|---|"]
            body += [f"| {r['option']} | {r.get('reason','—')} |"
                     for r in result["rejected"]]
            body += [""]
        if result.get("failures"):
            body += ["## Failures", ""]
            body += [f"- **{f['what']}** — {f.get('cause','cause not identified')}"
                     for f in result["failures"]]
            body += [""]
        if result.get("open"):
            body += ["## Open", ""]
            body += [f"- {o}" for o in result["open"]]
            body += [""]
        if result.get("references"):
            body += ["## References", ""]
            body += [f"- {r['url']} — {r.get('for','')}".rstrip(" —")
                     for r in result["references"]]
            body += [""]
        body += ["---", "",
                 f"*Distilled from a {len(parsed['turns'])}-turn "
                 f"{parsed['platform']} conversation by {result['_provider']}. "
                 "The transcript was not retained; the source URL above is the "
                 "only route back to it.*", ""]
    else:
        # No summary available and nothing sensitive: keep the transcript so the
        # content is not lost, and flag it for manual distillation.
        body += raw_transcript([], ["No summary was produced (all providers failed). Distil by hand,",
                                    "then delete the transcript below."],
                               [{"role": t["role"], "text": t["text"]} for t in parsed["turns"]])

    if dry_run:
        log(f"  [dry-run] would write {rel}.md "
            f"({len(parsed['turns'])} turns, tags={tags})")
        return None

    suggested = (result or {}).get("folder") or "inbox"
    cmd = [str(BASE / "scripts" / "newnote.sh"), "--tags", ", ".join(tags)]
    if suggested != "inbox":
        cmd += ["--field", f"suggested_folder: {suggested}"]
    subprocess.run(cmd + [rel, title, "note"], check=True, capture_output=True, text=True, cwd=REPO_ROOT)
    with target.open("a", encoding="utf-8") as fh:
        fh.write("\n" + "\n".join(body).rstrip() + "\n")
    return target


def process(path: Path, cfg: dict, state: dict, dry_run: bool) -> None:
    raw = path.read_text(encoding="utf-8", errors="replace")
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    if digest in state["seen"]:
        return

    parsed = parse_export(raw)
    if not parsed or not parsed["turns"]:
        log(f"{path.name}: not a recognisable export, skipping")
        return

    log(f"{path.name}: {parsed['platform']}, {len(parsed['turns'])} turns")

    conversation = "\n\n".join(
        f"{t['role']}: {t['text']}" for t in parsed["turns"])
    held = sensitivity_hits(raw)

    result = None
    if held:
        log(f"  HELD BACK ({', '.join(held)}) — not sent to any API")
    elif dry_run:
        log("  [dry-run] no API call")   # --dry-run promises exactly that
    else:
        result = call_provider(cfg, cfg["provider"], conversation)
        if result is None and cfg.get("fallback"):
            log(f"  falling back to {cfg['fallback']}")
            result = call_provider(cfg, cfg["fallback"], conversation)
        if result is None:
            log("  no summary available; filing raw")

    target = make_note(parsed, result, held, path, digest, dry_run)
    if dry_run:
        return
    if target is None:
        state["seen"][digest] = {"file": path.name, "status": "skipped"}
        return

    lint = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "lint.py"),
                           "--quiet"], capture_output=True, text=True, cwd=REPO_ROOT)
    if lint.returncode != 0:
        log(f"  LINT FAILED — the note is in inbox/ and will block every commit "
            f"of this repo until fixed:\n{lint.stderr.strip()}")
        state["seen"][digest] = {"file": path.name, "status": "lint-failed"}
        return

    log(f"  wrote {target.relative_to(REPO_ROOT)} and lint passed")
    state["seen"][digest] = {"file": path.name, "status": "filed",
                             "note": str(target.relative_to(REPO_ROOT)),
                             "at": dt.datetime.now().isoformat(timespec="seconds")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="parse and report, write nothing and call no API")
    ap.add_argument("--file", type=Path, help="process one specific file")
    ap.add_argument("--repo", type=Path, help="target repo (default: the git work tree you run this in)")
    args = ap.parse_args()

    global REPO_ROOT, INBOX, STATE_FILE, CONFIG_FILE, FOLDERS, SYSTEM_PROMPT
    REPO_ROOT = args.repo.resolve() if args.repo else find_repo_root()
    INBOX, STATE_FILE = REPO_ROOT / "inbox", REPO_ROOT / ".watcher-state.json"
    CONFIG_FILE = REPO_ROOT / "scripts" / "watcher.config.json"
    cfg = load_config()
    FOLDERS = list(cfg["folders"])
    SYSTEM_PROMPT = build_prompt(FOLDERS, cfg.get("context", []))
    state = load_state()
    INBOX.mkdir(parents=True, exist_ok=True)

    if args.file:
        if not args.file.is_file():
            log(f"--file: not a readable file: {args.file}")
            return 1
        candidates = [args.file]
    else:
        candidates = sorted(p for p in WATCH_DIR.glob("*.md")
                            if EXPORT_RE.match(p.name))

    if not candidates:
        return 0

    for path in candidates:
        try:
            process(path, cfg, state, args.dry_run)
        except Exception as exc:  # one bad file must not stop the rest
            log(f"{path.name}: unhandled {type(exc).__name__}: {exc}")
        if not args.dry_run:
            save_state(state)   # per file: a crash mid-batch must not forget the files done
    return 0


if __name__ == "__main__":
    sys.exit(main())
