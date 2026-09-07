# Claude client setup — what differs

**Read `Client-Setup.md` first** — the browser exporter, capture, the format that
works, what a connected client can see, and loading the brief are the same for
every client. This file holds only what is Claude-specific.

---

## Capturing from claude.ai — what differs

**Artifacts are not exported.** The exporter captures the conversation text.
Code or documents rendered as artifacts in the side panel are not in the file —
copy anything you need into the chat body *before* exporting, or save it
separately.

**The header renders late.** Claude builds its header after the messages, so a
reload is more often needed here than on the other platforms before the Export
button appears.

**Long thinking blocks inflate the export** without adding conclusions. This
costs distillation time, not quality — the distiller is instructed to keep the
destination and drop the walk.

---

# give it the vault through a Project

Everything in a Project's **knowledge** is visible to every conversation in that
Project. That is the persistence mechanism — a file dropped into one
conversation dies with it.

## Route A — Project knowledge synced from GitHub (best, if your plan shows it)

1. Run `~/kb/sync.sh` on the Mac. GitHub sync reads **pushed commits**.
2. claude.ai → **Projects → New project** → in the knowledge panel, look for
   **Add from GitHub** (wording varies: *Connect GitHub*, *Sync with GitHub*).
3. Authorise, then pick **`aiaibox/kb-public`, `kb-personal`, `kb-business`**.
   Leave `kb-private` out.
4. Re-sync from the same panel after `sync.sh` when you want it current.

## Route B — Project knowledge uploaded by hand (works on every plan)

Build the bundle on the Mac — ~5 s, expect 134 files:

```
rm -rf ~/Desktop/kb-share && mkdir -p ~/Desktop/kb-share && find ~/kb/public ~/kb/personal ~/kb/business -name '*.md' -not -path '*/_templates/*' -not -path '*/scripts/*' -not -path '*/setup/*' -not -name '*RULES.md' -not -name 'AGENTS.md' -not -name 'CLAUDE.md' -exec cp {} ~/Desktop/kb-share/ \; && ls ~/Desktop/kb-share | wc -l
```

Then **Projects → New project → knowledge → drag the folder's contents in**.
Refresh by re-running the command and re-uploading.

## Route C — GitHub's remote MCP server (only if Settings → Connectors offers *Add custom connector*)

Not every plan does; on Team/Enterprise only an org admin can add one. If the
button is there: URL `https://api.githubcopilot.com/mcp/`, authorise with read
scopes, then enable it **per conversation** via **+ → Connectors**. It reads
pushed commits, so `sync.sh` first.

**GitBook MCP is not a substitute.** It reads GitBook documentation spaces, not
GitHub repositories.

Persist the brief in a **Project's knowledge**, beside the notes.

---

# VS Code: Claude Code

**Installed and in use on this machine** (`anthropic.claude-code`). This is the
strongest way to work with the vault, and everything in Part 2 is a fallback for
when you are away from it.

## Why it beats every web route

| | Web UI | Claude Code |
|---|---|---|
| Sees | an uploaded snapshot, or pushed commits | the **live working tree** |
| Sync needed | re-upload, or `sync.sh` first | none |
| Can write notes | no | yes — through `newnote.sh`, so ULIDs are correct |
| Can run `lint.py` | no | yes |
| Can commit | no | yes |
| `private/` | ciphertext, or absent | **decrypted and readable — the boundary is the instruction, not the crypto** |

## Setup — nothing to install beyond the extension

Open `~/kb` as the folder. Instruction files load automatically:

| Where you start | What loads |
|---|---|
| `~/kb` | `~/kb/AGENTS.md` — the vault map |
| `~/kb/personal` | that **plus** `personal/AGENTS.md` — layout, domain rules, boundaries |

**Start in the repo you intend to work in.** Opening `~/kb` and asking about
investments means the `personal` domain rules never load. `cd ~/kb/personal`
first, or use `kbp`.

## Getting good answers

1. **Ask through the topic notes.** "What is my current allocation?" resolves to
   `finance/invest/portfolio-map.md` in one hop.
2. **`kbs <keyword>`** when you want the file rather than an answer. `private/` is
   excluded from it.
3. **Let it write.** "Create a note for this in `living/`" produces a correct
   ULID, valid frontmatter and a lint-clean file. Writing the file by hand or
   letting a model invent one is how frontmatter breaks.
4. **`python3 scripts/lint.py` before finishing.** The pre-commit hook enforces it
   anyway, but finding out earlier is cheaper.

## The one rule that is not enforced by code

`private/` is decrypted in your working tree. Encryption protects it at rest on a
remote; it does **not** hide it from an agent with filesystem access. The only
thing keeping it out of a conversation is the instruction in
`private/AGENTS.md`. Do not point an agent at it.
