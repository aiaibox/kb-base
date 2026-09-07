# kb-base

**This repo is public and holds no notes.** It is the one copy of the machinery
that four content repos share: `scripts/lint.py`, `scripts/newnote.sh`,
`.githooks/pre-commit`, `_templates/`, `tags.txt`, `RULES.md`, `WORKING-RULES.md`.

Read `RULES.md` (what a note is, which repo, folders, tags) and
`WORKING-RULES.md` (how to behave while working) before touching anything.

## How the sharing works

Nothing is copied or distributed. Each content repo sits beside this one —
`~/kb/base`, `~/kb/public`, `~/kb/personal`, … — and:

- points its git hooks here: `git config core.hooksPath ../base/.githooks`
  (per clone; set in `New-Machine-Setup.md`)
- runs the tools from here **inside its own work tree**:
  `python3 ../base/scripts/lint.py`, `../base/scripts/newnote.sh <path> "<title>"`

The tools derive the target repo from `git rev-parse --show-toplevel` of the
working directory, never from where this file lives. Repo-specific rules live in
`<repo>/scripts/lint-local.py` and are loaded into the same lint report —
`public` bans private IPs and internal hostnames; `private` requires numeric
filenames and decrypts every encrypted blob. This repo has none.

## Rules for changing anything here

1. **A change here changes all four repos at once.** Run
   `for r in public personal business private; do (cd ../$r && python3 ../base/scripts/lint.py); done`
   and get four `clean` lines before pushing.
2. **Nothing private, ever.** No names, hosts, paths that identify a person or
   employer. `lint.py` secret-scans this repo's own files on every run.
3. **Adding a tag is a deliberate edit** to `tags.txt`, not something done while
   filing a note.
4. `WORKING-RULES.md` §7 applies to this repo most of all: delete what is
   redundant.

## The one failure mode to know

If a content repo is cloned without this one beside it, `core.hooksPath` points
at nothing and **git runs no hooks and says nothing**. Clone `base` first.
