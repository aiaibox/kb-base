# Client setup — what every client shares

Do this **once**. Then read the per-client file — `ChatGPT-`, `Claude-` or
`Gemini-Client-Setup.md` — for the parts that differ: how that client connects to
the vault, where its brief persists, and its VS Code extension.

## What it is

The vault is fed by one click in the browser. A userscript adds an **Export**
button to AI chat pages; the file lands in `~/Downloads`; a launchd watcher picks
it up, distils it and files a note in `personal/inbox/`.

You choose what gets captured. Nothing is exported automatically.

## 1. Use Chrome

**Violentmonkey has no Safari build** — Safari uses a different extension API.
Keep Safari for normal browsing; do AI chats in Chrome when you intend to keep
the conversation.

## 2. Install Violentmonkey

Chrome Web Store → *Violentmonkey* → **Add to Chrome**. ~1 min.

Open-source userscript host. Tampermonkey is the better-known equivalent but
went partly closed-source.

## 3. Install OmniChat Exporter

<https://greasyfork.org/en/scripts/567743-omnichat-exporter-export-any-ai-chat-instantly>

**Audit the script before confirming** — open the `/code` tab and read the
`@connect` block. It is an allowlist Violentmonkey enforces: `GM_xmlhttpRequest`
can reach *only* those hosts. Confirm none of them could receive a conversation.

Then **Install this script** → **Confirm installation**. ~2 min including the audit.

## 4. Verify

Open any AI chat **with at least one message in it** and look for the Export
button in the conversation header. Violentmonkey's toolbar icon should show **1**
active script on that tab.

| Symptom | Cause |
|---|---|
| No button | Page rendered before the script (`@run-at document-idle`) — reload |
| No button, icon shows **0** | URL didn't match the script's `@match` |
| No button on a new chat | Header controls render only once a conversation exists |

## The only format that works

The watcher parses **Markdown** exports. If the exporter offers a format choice,
pick Markdown — not PDF, PNG or plain text.

A usable file has:

- a filename `<platform>-<slug>-<ISO timestamp>Z.md`, e.g.
  `chatgpt-tomato-flavour-2026-09-06T09-48-00-256Z.md`
- a first line `# <Platform> Export`
- turn delimiters that are exactly `## User` and `## Assistant`

A plain-text export uses `User:` instead, parses to zero turns, and is skipped
with *"not a recognisable export"* in the log.

**Check a file you just exported** — expect a filename and a count of at least 2:

```
ls -t ~/Downloads/*.md | head -1 && grep -c '^## \(User\|Assistant\)$' "$(ls -t ~/Downloads/*.md | head -1)"
```

## What happens next

Saving into `~/Downloads` triggers the watcher within ~30 s. Distillation takes
**~2 minutes per conversation**. The note appears in `personal/inbox/`.

```
tail -5 ~/kb/.watcher.log
```

Nothing is deleted from `~/Downloads`; clean it up yourself when you like.

**Never unzip a bulk archive into `~/Downloads`.** The watcher is live on that
folder and will start processing every file at ~2 min each. Unzip elsewhere.

---

# Capture a conversation into the vault

1. **Open the conversation in Chrome** — `chatgpt.com`, `claude.ai` or
   `gemini.google.com`, signed in, in a conversation that already has messages.
2. **Click Export in the conversation header** and choose **Markdown**. The file
   saves to `~/Downloads` as `<platform>-<slug>-<ISO timestamp>Z.md`.
3. **Wait.** The watcher fires within ~30 s and takes **~2 minutes** to distil.
4. **Verify — on the Mac running the watcher:**

```
tail -5 ~/kb/.watcher.log
```

**Expect:** a line naming your file, then `wrote inbox/<date>-<slug>.md and lint passed`.
Then `ls -t ~/kb/personal/inbox/*.md | head -1` to read the note.

## If nothing appears

| Check | Command / action |
|---|---|
| File landed with the right name? | `ls -t ~/Downloads/*.md \| head -1` |
| Right format? | `grep -c '^## \(User\|Assistant\)$'` on that file — must be ≥2 |
| Watcher running? | `launchctl list \| grep com.kb.watcher` |
| Watcher can read `~/Downloads`? | See Full Disk Access in `New-Machine-Setup.md` — **this fails silently with an empty log** |

---

---

# What a connected client can see — decided 2026-09-06

Three repos are connected; `private` is not.

| Repo | Visible | Consequence |
|---|---|---|
| `kb-public` | plaintext | Intended. Written for strangers anyway |
| `kb-personal` | **plaintext** | Deliberate: answering from real notes was judged worth it |
| `kb-business` | **plaintext** | Employer material. Same trade, same reasoning |
| `kb-private` | **not connected** | Balances, diagnoses, legal, identity. Ciphertext even if it were |

The `private` row is the payoff from mandatory encryption: it stays out of reach
by construction, not by remembering to exclude it.

**Run `~/kb/sync.sh` first.** The connector reads pushed commits, so anything
uncommitted or unpushed is invisible to it.

---

---

# Load the brief

A connector or an upload gives access. **`web-brief.md`** tells the model how to
read what it finds — the note structure, which tags change how a note should be
trusted, the rules it must follow — and covers both live and snapshot access. It
is written to be read by the model: paste or upload it as-is.

A file in a single conversation dies with it. Put the brief where the client
persists things:

| Client | Where it persists |
|---|---|
| ChatGPT | a **Project** — every conversation in it sees the Project's files |
| Claude | a **Project** |
| Gemini | a **Gem** — its instructions and files persist across sessions |

**Verify it worked** — ask:

> *Read `index.md` from `aiaibox/kb-personal` and list the areas it covers.*

**Expect:** the ten top-level folders. If it guesses or apologises, the files are
not in reach — the connector is off for this conversation, or the upload is not
in the Project.

---

# VS Code — the caveat every agent shares

Any VS Code agent has filesystem access to the decrypted `private/` working
tree. The boundary is the instruction in `private/AGENTS.md`, not the
encryption. Verify a new agent honours it before trusting it near `~/kb`.
