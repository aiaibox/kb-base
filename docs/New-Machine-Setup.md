# New machine setup

Brings a fresh Mac to a fully working vault: four repos, encryption, capture
pipeline, weekly review.

**Before you start you need:** an admin account, GitHub access to the `aiaibox`
org, and your password manager open — it holds the **git-crypt key**.
Without it `private/` can be cloned but never read.

Every step below is run **on the new Mac**. Total ~40 min, most of it waiting on
Homebrew.

---

## 1. Command line tools and Homebrew  · ~15 min

```
xcode-select --install
```
Expect a GUI installer. Wait for it to finish before continuing.

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
~10 min. Follow the printed instruction to add `brew` to your PATH, then:

```
brew install git-crypt gh ripgrep fd fzf bat glow
```
~3 min. **Expect:** all seven installed, no errors.

## 2. Authenticate GitHub  · ~2 min

```
gh auth login
```
Choose GitHub.com → HTTPS → login with a browser. **Expect:** `Logged in as <you>`.

## 3. Clone the four repos  · ~1 min

```
mkdir -p ~/kb && cd ~/kb && for r in base public personal business private; do gh repo clone aiaibox/kb-$r $r; done
```
**Expect:** five directories. `base` first — it holds the one copy of lint, newnote,
templates and rules that every other repo's hooks point at. `private/` is ciphertext at this point — its notes
are unreadable binary until step 5.

## 4. Lock down private  · instant

```
chmod 700 ~/kb/private
```
**Expect:** no output. Verify with `stat -f '%Sp' ~/kb/private` → `drwx------`.

## 5. Unlock private  · ~2 min

Export the git-crypt key from your password manager to a file, then:

```
cd ~/kb/private && git-crypt unlock /path/to/kb-private.key
```
**Expect:** no output, and `cat ~/kb/private/finance/accounts/*.md` now shows
readable text. **Delete the key file afterwards** — the password manager stays the only copy.

```
cd ~/kb/private && git-crypt status | grep -c 'not encrypted'
```
**Expect:** a small number (~29). Those are machinery — dotfiles, `scripts/`,
`scripts/lint.py`, `AGENTS.md`, `CLAUDE.md`. If any *note* appears there, stop
and fix `.gitattributes` before committing anything.

## 6. Enable the pre-commit hook in all four repos  · instant

```
for r in public personal business private; do git -C ~/kb/$r config core.hooksPath ../base/.githooks; done && git -C ~/kb/base config core.hooksPath .githooks
```
**Expect:** no output. This is what makes lint block a bad commit; it is
per-clone and is **not** carried by the repo. **If `base` is missing, git runs no
hooks and says nothing** — commits land unlinted. Step 3 clones it first for that reason.

## 7. Shell helpers and sync  · ~1 min

```
mkdir -p ~/.zsh.d && ln -sfn ~/kb/personal/setup/70-kb.zsh ~/.zsh.d/70-kb.zsh && ln -sfn personal/setup/sync.sh ~/kb/sync.sh
```

Ensure `~/.zshrc` sources the directory — add this line if absent:

```
for f in ~/.zsh.d/*.zsh(N); do source "$f"; done
```

Open a new terminal. **Expect:** `kb`, `kbp`, `kbs`, `kblint` all work.

## 8. API keys into Keychain  · ~2 min

Two providers: GLM primary, DeepSeek fallback. Keys come from
`open.bigmodel.cn` and `platform.deepseek.com`.

```
security add-generic-password -U -s kb-glm-api-key -a "$USER" -w 'PASTE_YOUR_BIGMODEL_KEY'
```

```
security add-generic-password -U -s kb-deepseek-api-key -a "$USER" -w 'PASTE_YOUR_DEEPSEEK_KEY'
```

**Expect:** no output from either. Verify:

```
security find-generic-password -s kb-glm-api-key -w | head -c 8
```
**Expect:** the first 8 characters of your key.

## 9. Install the two launchd agents  · ~1 min

```
for a in watcher review; do sed "s|__HOME__|$HOME|g" ~/kb/personal/setup/com.kb.$a.plist > ~/Library/LaunchAgents/com.kb.$a.plist && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kb.$a.plist; done
```

```
launchctl list | grep com.kb
```
**Expect:** two lines, `com.kb.watcher` and `com.kb.review`, both with exit code `0`.

## 10. Full Disk Access — the step that silently breaks everything  · ~2 min

System Settings → Privacy & Security → **Full Disk Access** → **+** → press
`⌘⇧G`, enter `/usr/bin/python3`, add it. Repeat for `/bin/bash`.

Without this, the watcher runs, exits 0, and reads **nothing** from `~/Downloads`.
The log stays empty and there is no error anywhere. Budget for this being the
cause whenever captures silently stop.

Restart the agents so they inherit the grant:

```
for a in watcher review; do launchctl kickstart -k gui/$(id -u)/com.kb.$a; done
```

## 11. Obsidian  · ~3 min

Install Obsidian, then **Open folder as vault** → `~/kb`.

**Open `~/kb`, never `~/kb/private`.** Opening `private` directly drops an
`.obsidian/workspace.json` that records the filenames you opened — defeating the
point of numeric filenames.

The shipped config already excludes `private/` from indexing:

```
cp ~/kb/personal/setup/obsidian-app.json ~/kb/.obsidian/app.json
cp ~/kb/personal/setup/obsidian-appearance.json ~/kb/.obsidian/appearance.json
```
Restart Obsidian. **Expect:** `private/` absent from search and the file tree.

## 12. Vault-root symlinks  · instant

`~/kb` itself is not a repo, so three symlinks are recreated by hand. `AGENTS.md`
at the root is what gives a session started there any vault context; agents look
for it (and `CLAUDE.md`) in the working directory, and `~/kb` is the default.

```
cd ~/kb && ln -sfn base/AGENTS.md AGENTS.md && ln -sfn AGENTS.md CLAUDE.md && ln -sfn base/.editorconfig .editorconfig
```
**Expect:** no output. `ls -l ~/kb/*.md` shows both pointing into `base`.

## 13. Verify the whole thing  · ~3 min

```
for r in base public personal business private; do (cd ~/kb/$r && python3 scripts/lint.py); done
```
**Expect:** five `clean` lines (`base` reports 0 notes). Warnings are fine; problems are not.

```
python3 ~/kb/personal/scripts/review.py
```
**Expect:** the weekly digest — note counts, empty inboxes, lint and drift all `ok`.

End-to-end capture test: follow `Client-Setup.md`, export one
conversation, then after ~2 min:

```
tail -5 ~/kb/.watcher.log
```
**Expect:** `wrote inbox/<date>-<slug>.md and lint passed`.

---

## What is deliberately not automated

- **`private/` is absent from `sync.sh`** and pushed by hand, after
  `git-crypt status -e` confirms every content file is encrypted.
- **Nothing routes to `public/`.** It is pushed automatically, so material
  arrives only by being written for it or restated into it.

## Failure table

| Symptom | Cause |
|---|---|
| Watcher exits 0, log empty, no notes | Full Disk Access (step 10) |
| `git-crypt unlock` fails | Wrong key, or repo already unlocked |
| `private/` notes look like binary | Step 5 not done |
| Bad commit accepted | `core.hooksPath` not set (step 6) |
| Export ignored, log says "not a recognisable export" | Plain-text instead of Markdown export |
| Distillation hangs past ~5 min | Provider outage — the fallback chain is GLM → DeepSeek |
