# ~/kb — five repos, one Obsidian vault

Plain Markdown in git, so no vendor owns it. `~/kb` itself is not a repo; the five
below are. This file loads for every session in the vault. Each repo's own
`AGENTS.md` loads on top when you work inside it, so **`cd` into the repo you mean
first** or its rules never load. Your working directory is then the repo root:
never prefix a path with `kb/` or the repo name.

| Repo | Ask before filing | Remote |
|---|---|---|
| `base/` | **No notes.** One copy of lint, newnote, templates, tags, rules, docs | public |
| `public/` | *Would I put this on a blog?* Permanent: history cannot be unpublished | public |
| `personal/` | *Would I show a friend?* **The default** when the ladder does not resolve | private |
| `business/` | *Is this the employer's?* One employer; people who did not consent | private |
| `private/` | *Only my spouse, or nobody?* Status, not reasoning. git-crypt | private |

Aliases: `kb` `kbp` `kbb` `kbu` `kbpriv` `kbin` `kbsync`.

## Hard rules

1. **IMPORTANT: never read, list, summarise or quote `private/`.** Its working
   tree is decrypted, so encryption does not stop you. A `Read(~/kb/private/**)`
   deny rule in `~/.claude/settings.json` blocks the file tools, `@` mentions,
   IDE context and `cat`-style Bash reads; it does not block a script that opens
   a file itself, so the instruction still carries the rest. If a task seems to
   need something from there, stop and ask for that fact directly.
2. `../base/scripts/newnote.sh`, run inside the target repo, is the only way to
   create a note. It writes the ULID and the frontmatter, so nothing has to
   rewrite them afterwards.
3. `python3 scripts/lint.py` before finishing. The hook only catches what reaches
   a commit, and most sessions end without one.
4. Nothing reaches `public/` by moving a file. A move carries the original's
   history, and history is the one thing `public` cannot take back. Restate the
   sanitised fact as a fresh note; leave the original where it is.
5. Merge before you create, and record conclusions rather than conversation. Two
   notes on one subject are found by neither search, and the conversation is
   scaffolding that comes down once the note stands. Extend the note that already
   answers the question; 400 lines is the soft ceiling, 600 the hard stop. The
   merge and split procedures are `RULES.md` §4: follow them, do not improvise.
6. Never invent a folder. The declared sets are `RULES.md` §2. A declared one
   that is missing was lost to git not tracking directories: recreate it with a
   `.gitkeep`.
7. Read `base/docs/Distillation-Playbook.md` before any import, triage, merge or
   audit. It carries the failure modes of the first full pass.
8. Before writing or merging a note, read `RULES.md` §3 for who the note is for
   and what success looks like, and §4 for what to do when two of these rules
   pull against each other.

Run `/context` to confirm this file and the repo's own loaded; `/doctor` proposes
trims for a checked-in instruction file.

## Where the detail lives

| Question | File |
|---|---|
| What a note must contain, which repo, tags, size, merge and split | `base/RULES.md` |
| How to behave: output, exact CLI, name the machine, change table | `base/WORKING-RULES.md` |
| Turning chat exports into notes without leaking status or secrets | `base/docs/Distillation-Playbook.md` |
| A fresh Mac, end to end | `base/docs/New-Machine-Setup.md` |
| Capture from a browser chat, per client | `base/docs/Client-Setup.md` |
| Architecture, where things go, what an AI can see | `personal/tech/kb/kb-system.md`, `kb-directory-scaffold.md`, `ai-access.md` |

## What runs without being asked

`com.kb.watcher` distils a chat exported into `~/Downloads` and lands it in
`personal/inbox/`, always, whatever the subject. `com.kb.review` reports on Monday.
`~/kb/sync.sh` pulls, lints, commits and pushes every repo except `private`, which
it only pulls. Nothing else is automatic, and nothing is pushed on your behalf
during a session.
