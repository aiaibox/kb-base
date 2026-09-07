# ChatGPT client setup — what differs

**Read `Client-Setup.md` first** — the browser exporter, capture, the format that
works, what a connected client can see, and loading the brief are the same for
every client. This file holds only what is ChatGPT-specific.

---

## Capturing from chatgpt.com — what differs

**Consecutive assistant blocks.** ChatGPT emits several `## Assistant` blocks in
a row where the other platforms emit one. The watcher merges same-role runs, so
this is handled — but it is why a ChatGPT export can look oddly segmented if you
open the raw file.

**Long conversations are the common case here.** The distiller keeps the
conclusion and drops the walk to it, so a 58-turn thread still becomes one note.
If a single thread covered several unrelated subjects, expect one note per
subject, and check `personal/inbox/` for more than one new file.

**The official ChatGPT export (`conversations.json`) does not work.** Only
OmniChat Markdown is parsed. A bulk archive needs a converter first — ask before
unzipping anything into `~/Downloads`.

---

# Connect the vault

## GitHub connector — ~5 min, once

1. Run `~/kb/sync.sh` on the Mac. The connector reads **pushed commits**.
2. ChatGPT → **Settings → Connectors** → connect **GitHub**, authorise in the
   browser.
3. Grant **read** scopes. Write access lets it open pull requests; you do not
   need that for answering questions.
4. Select the repositories: **`kb-public`, `kb-personal`, `kb-business`**.
   Leave `kb-private` unselected.

Persist the brief in a **Project**; create one Project for the vault and keep it there.

---

# VS Code: Codex

**Not installed on this machine — the steps below are the convention, not
something verified here.** Only `anthropic.claude-code` is present.

OpenAI's VS Code extension is **Codex**. It reads **`AGENTS.md`** from the
working directory and its parents — the same open convention the vault already
follows, which is why every repo here has a real `AGENTS.md` with `CLAUDE.md` as
a symlink to it.

So if you install Codex, it picks up the vault instructions with **no extra
setup**: `~/kb/AGENTS.md` and each repo's `AGENTS.md` are already the right
filename in the right place.

## What to check on first use

```
ls -l ~/kb/AGENTS.md ~/kb/personal/AGENTS.md
```
**Expect:** both present. If Codex does not appear to have read them, ask it
directly what instruction files it loaded before assuming it did.
