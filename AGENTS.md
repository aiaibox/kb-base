# kb-base — the shared machinery

No notes. One copy of everything the other four repos run: `scripts/` (lint and
the shared library it exposes, newnote, watcher, review, the importers and
exporters), `_templates/`, `tags.txt`, `.githooks/`, `RULES.md`,
`WORKING-RULES.md`, `docs/`. Nothing here is copied or distributed; the repos
reach in.

**A change here changes every repo at once.** Before pushing:

```
for r in ../*/; do (cd $r && python3 scripts/lint.py); done    # want five clean lines
```

## Rules

- **Nothing private, ever.** No name, host or path that identifies a person or an
  employer. This repo is world-readable, and lint secret-scans its own files.
- **Adding a tag is a deliberate edit to `tags.txt`**, never a side effect of filing.
- **Tools derive their target from the git work tree they run in**, never from
  where a file sits. Keep it that way: base knows nothing about the repos.
- Each content repo has an eight-line `scripts/lint.py` that imports this one and
  calls `main(local=check)` with its own rule. `public` bans private IPs and
  internal hostnames, `private` requires numeric filenames and decrypts every
  blob, `personal` and `business` add none.
- The watcher's household context and folder list live in the **target** repo's
  `scripts/watcher.config.json`, read at run time. Not here.
- A content repo cloned without `base` beside it has `core.hooksPath` pointing at
  nothing, so **git runs no hooks and says nothing**. Clone `base` first.
