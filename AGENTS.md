# ~/kb — the vault, and kb-base

Five sibling git repos under one Obsidian vault. This file is `kb-base`'s own
and is also symlinked to `~/kb/AGENTS.md`, so it loads for any session started at
the vault root. **Each content repo has its own `AGENTS.md` with the rules that
matter there — start in the repo you intend to work in, or those never load.**

```
cd ~/kb/personal    # or kbp / kbb / kbu
```

| Repo | Holds | Remote |
|---|---|---|
| `base/` | **No notes.** The one copy of lint, newnote, templates, tags, the rules, and the setup docs | public |
| `public/` | Written for a stranger. World-readable, permanently | public |
| `personal/` | **The default.** Preferences, systems, how you think about money and health | private |
| `business/` | One employer: their systems, projects, colleagues | private |
| `private/` | Status, not reasoning. Encrypted with git-crypt | private |

## Read first

- `base/RULES.md` — what a note must contain, which repo, folder sets, tags, tiers.
- `base/WORKING-RULES.md` — how to behave: minimal output, exact CLI, name the
  machine, estimate anything slow, end with a change table, delete redundancy.
- `personal/tech/kb/kb-system.md` — architecture. `kb-directory-scaffold.md` —
  where things go. `ai-access.md` — what any AI can and cannot see.

## Hard rules

1. **`private/` is never read, summarised, indexed, quoted or listed.** Its
   working tree is decrypted, so encryption does not stop you — the instruction
   does. If a task seems to need something from it, stop and ask.
2. **`../base/scripts/newnote.sh`, run inside the target repo, is the only correct
   way to create a note.** It takes `--tags`, `--created`, `--updated` and
   `--field`, so nothing ever rewrites frontmatter afterward.
3. **`python3 scripts/lint.py` before finishing.** Each repo's `scripts/lint.py`
   runs base's rules then its own; the pre-commit hook enforces it.
4. **Nothing is promoted to `public/` by moving it.** Write a fresh sanitised
   note; leave the original where it is.
5. **Never create a folder outside the declared sets** in `RULES.md` §2. A
   *declared* folder that is missing was lost to git not tracking directories —
   recreate it and add a `.gitkeep`.

## Capture pipeline

Export a chat from the browser into `~/Downloads` → the `com.kb.watcher` launchd
agent distils it (~30 s to fire, ~2 min to run) → a note lands in
**`personal/inbox/`**, always, regardless of subject. Nothing is committed or
pushed automatically. `com.kb.review` runs Monday 09:00 and reports what needs a
human. `~/kb/sync.sh` pulls, lints, commits and pushes every repo except
`private`, which it only pulls.

## Setup and client docs — `base/docs/`

- `New-Machine-Setup.md` — a fresh Mac, end to end
- `Client-Setup.md` — capture from any browser chat, what a connected client can
  see, loading the brief; then `ChatGPT-`, `Claude-`, `Gemini-Client-Setup.md`
  for what differs per client
- `web-brief.md` — model-facing; paste or upload as-is

## This repo — kb-base

Everything shared lives here **once**: `scripts/lint.py`, `scripts/newnote.sh`,
`.githooks/pre-commit`, `_templates/`, `tags.txt`, `RULES.md`,
`WORKING-RULES.md`, `.editorconfig`, `docs/`. Nothing is copied or distributed.
Each content repo points its hooks here (`git config core.hooksPath
../base/.githooks`, per clone) and has an 8-line `scripts/lint.py` that imports
this repo's and calls `main(local=check)` with its own rules — `public` bans
private IPs and internal hostnames; `private` requires numeric filenames and
decrypts every encrypted blob; `personal` and `business` have none. The tools
derive the target repo from the git work tree they run in, never from where a
file lives.

- **A change here changes every repo at once.** Get five `clean` lines from
  `for r in ../*/; do (cd $r && python3 scripts/lint.py); done` before pushing.
- **Nothing private, ever.** No names, hosts or paths that identify a person or
  employer. Lint secret-scans this repo's own files on every run.
- **Adding a tag is a deliberate edit** to `tags.txt`.
- If a content repo is cloned without this one beside it, `core.hooksPath` points
  at nothing and **git runs no hooks and says nothing**. Clone `base` first.
