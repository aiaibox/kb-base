# Gemini client setup — what differs

**Read `Client-Setup.md` first** — the browser exporter, capture, the format that
works, what a connected client can see, and loading the brief are the same for
every client. This file holds only what is Gemini-specific.

---

## Capturing from gemini.google.com — what differs

**Check the `URL:` line in the exported file.** Gemini share/app URLs are the
only route back to the original conversation — the transcript is not retained
after distillation, so a wrong URL means the source is gone. Some exports have
carried a URL that does not match the platform; open the note's `**Source:**`
line once and confirm it resolves.

**Google account switching.** With several signed-in accounts, Gemini can render
under `/u/1/` style paths that the script's `@match` may not cover. If the Export
button never appears, open the conversation in a window signed in to only one
account.

**Grounded answers cite sources inline.** Those citations survive into the note's
`## References` section, which is usually the most valuable part of a Gemini
capture — do not strip them at triage.

---

# Give it the files

## There is no connector route here

Unlike ChatGPT and Claude, Gemini has no repository connector worth relying on.
It reads a **snapshot you upload**, so it is always as stale as your last upload —
and the brief tells it to say so rather than pretend otherwise.

## Build the snapshot — ~5 s

```
rm -rf ~/Desktop/kb-share && mkdir -p ~/Desktop/kb-share && find ~/kb/public ~/kb/personal ~/kb/business -name '*.md' -not -path '*/_templates/*' -not -path '*/scripts/*' -not -path '*/setup/*' -not -name '*RULES.md' -not -name 'AGENTS.md' -not -name 'CLAUDE.md' -exec cp {} ~/Desktop/kb-share/ \;
```

**Expect:** 134 files, ~750 KB. Filenames collide only if two repos hold the same
basename, which the date prefixes make unlikely.

For a smaller, more stable upload, take `public/` plus the `topic` notes only —
those hold the current picture rather than every atomic fact.

Refresh by re-running the command and re-uploading.

Persist the brief in a **Gem**.

---

# VS Code: Gemini Code Assist

**Not installed on this machine — the steps below are the convention, not
something verified here.** Only `anthropic.claude-code` is present.

Google's VS Code extension is **Gemini Code Assist**. Google's agent tooling uses
**`GEMINI.md`** as its instruction file rather than `AGENTS.md`. The vault does
not ship one, because writing an instruction file for a tool nobody has installed
is how documentation goes stale.

## If you install it

Point it at the file that already exists rather than maintaining a second copy:

```
ln -s AGENTS.md ~/kb/GEMINI.md && ln -s AGENTS.md ~/kb/personal/GEMINI.md
```
**Expect:** no output. This is the same trick the vault already uses for
`CLAUDE.md`, which is a symlink to `AGENTS.md` in all four repos — one file,
several names, no drift.

Then confirm it actually read it: ask the assistant what instruction files it
loaded. If it did not, fall back to pasting the relevant `AGENTS.md` at the top
of a session.
