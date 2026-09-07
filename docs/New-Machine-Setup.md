# New machine setup

Brings a fresh Mac to a fully working vault: four repos, encryption, capture
pipeline, weekly review.

**Before you start you need:** an admin account, GitHub access to the `aiaibox`
org, and your password manager open — it holds the **git-crypt key**.
Without it `private/` can be cloned but never read.

Every step below is run **on the new Mac**. Total ~45 min, most of it waiting on
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
**If this Mac already holds a work GitHub account, do step 2a instead of relying on
HTTPS** — the shared keychain entry will make the private clones present the wrong login.

## 2a. Two GitHub accounts on one Mac  · ~5 min

Git's only credential helper on a stock Mac is `osxkeychain` (from Xcode's system
gitconfig), which caches **one** github.com credential per host, not per account — so
the private clones keep presenting the work login and fail exactly as if the login
had not happened. `gh auth setup-git` "fixes" it by coupling git to whichever `gh`
account is active, which makes every work repo follow `gh auth switch` too. The clean
split is SSH with a host alias plus a directory-scoped identity:

```
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_aiaibox -C aiaibox-kb
cat >> ~/.ssh/config <<'EOF'
Host github.com
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
Host github-aiaibox
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_aiaibox
  IdentitiesOnly yes
EOF
printf '[user]\n\tname = aiaibox\n\temail = 322385153+aiaibox@users.noreply.github.com\n' > ~/.gitconfig-kb
git config --global includeIf."gitdir:~/kb/".path ~/.gitconfig-kb
```

Add `~/.ssh/id_ed25519_aiaibox.pub` at github.com/settings/keys as `aiaibox` (or
`gh auth login --git-protocol ssh` and let it upload; `gh` holds both accounts and
`gh auth switch` then affects only `gh` commands, never git). In step 3 clone with the
alias — `git clone git@github-aiaibox:aiaibox/kb-personal.git personal` — instead of
`gh repo clone`. The noreply address keeps a real email out of `kb-public`'s permanent,
world-readable history.

**Verify:** `ssh -T github-aiaibox` → `Hi aiaibox!`; `ssh -T git@github.com` still
names the work account; `git -C ~/kb/personal config user.email` shows the noreply
address while a repo outside `~/kb` still shows the work identity.
**Never run `gh auth setup-git`** in this arrangement.

## 3. Clone the four repos  · ~1 min

```
mkdir -p ~/kb && cd ~/kb && for r in base public personal business private; do gh repo clone aiaibox/kb-$r $r; done
```
(With step 2a: `for r in …; do git clone git@github-aiaibox:aiaibox/kb-$r.git $r; done`.)
**Expect:** five directories. `base` first — it holds the one copy of lint, newnote,
templates and rules that every other repo's hooks point at. `private/` is ciphertext at this point — its notes
are unreadable binary until step 5.

## 4. Lock down private  · instant

```
chmod 700 ~/kb/private
```
**Expect:** no output. Verify with `stat -f '%Sp' ~/kb/private` → `drwx------`.

## 5. Unlock private  · ~2 min

Export the git-crypt key from your password manager to a file. A git-crypt key file
is **binary, 148 bytes**: 12-byte magic `\0GITCRYPTKEY` (it starts with a NUL),
`00 00 00 02`, a 32-byte AES-256 key, a 64-byte HMAC key, four zero bytes, no
trailing newline. Stored as text it is base64 — always **200 characters ending
`AA==`**. If the password manager holds it as an attachment, pass the downloaded file
straight to `git-crypt unlock` with no base64 step; if it holds the base64 text:

```
v='PASTE_VALUE'; echo "length=${#v}  last4=${v: -4}"          # expect 200 / AA==
( umask 077; printf '%s' "$v" | base64 -d > ~/kbkey )          # printf, not echo
test "$(wc -c < ~/kbkey)" -eq 148 && head -c 12 ~/kbkey | xxd  # 0047 4954 4352 5950 544b 4559
cd ~/kb/private && git-crypt unlock ~/kbkey; rm -f ~/kbkey      # ';' not '&&': a failed unlock must not leave the key on disk
```
**Expect:** no output from the unlock, and `cat ~/kb/private/finance/accounts/*.md`
now shows readable text. **Delete the key file afterwards** — the password manager
stays the only copy. `base64: error decoding base64 input stream` (seen 2026-09-06)
means the clipboard held the shell prompt line, not the key; 64 hex characters is
the bare AES key, which git-crypt cannot consume.

`encrypted file has been tampered with` on unlock means a **corrupt blob, not a wrong
key**: a wrong AES-CTR key gives ~25% printable garbage from byte 0, a damaged blob
decrypts cleanly to an offset (94% printable). `git-crypt status -e` only reads
`.gitattributes` and passes corrupt blobs; the real check decrypts each one — run it
here and before every push of `private`:

```
cd ~/kb/private && fail=0; for f in $(git ls-files); do b=$(git cat-file -p "HEAD:$f" 2>/dev/null | head -c 9 | xxd -p); [ "$b" = 004749544352595054 ] || continue; git cat-file -p "HEAD:$f" | git-crypt smudge >/dev/null 2>&1 || { echo "CORRUPT: $f"; fail=1; }; done; [ $fail = 0 ] && echo "all encrypted blobs decrypt"
```
**Expect:** `all encrypted blobs decrypt`.

```
cd ~/kb/private && git-crypt status | grep -c 'not encrypted'
```
**Expect:** a small number (17 on 2026-09-07, ~29 earlier — the count moves). Those are
machinery — dotfiles, `scripts/`, `scripts/lint.py`, `AGENTS.md`, `CLAUDE.md`. The
rule is: if any *note* appears there, stop and fix `.gitattributes` before committing
anything.

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

**The trap:** with Homebrew installed, bare `python3` is Homebrew's (3.13/3.14 at
`/opt/homebrew/bin/python3`) while the plists hardcode `/usr/bin/python3` (Apple's
3.9.6). Grant FDA to the Homebrew binary and the watcher fails silently forever.
Check the one you are adding: `/usr/bin/python3 -V` → `Python 3.9.6` (the three
scripts compile and run under 3.9.6 — verified 2026-09-05).

Without the grant, the watcher runs, exits 0, and reads **nothing** from `~/Downloads`.
The log stays empty and there is no error anywhere: `watcher.py` returns before
logging when `WATCH_DIR.glob("*.md")` finds nothing, and `pathlib.glob` swallows
`PermissionError` — a TCC denial and "no matching files" are byte-identical (empty
log, exit 0, `runs` counting up). So `launchctl list` proving the agent fires proves
nothing about the grant. Budget for this being the cause whenever captures silently
stop.

Restart the agents so they inherit the grant:

```
for a in watcher review; do launchctl kickstart -k gui/$(id -u)/com.kb.$a; done
```

**Decisive test** — a file whose name matches the export pattern but whose content
does not; it logs before any network call and writes no note:

```
printf 'not an export\n' > ~/Downloads/claude-fdatest-2026-09-06T12-00-00-000Z.md
sleep 40; cat ~/kb/.watcher.log
rm -f ~/Downloads/claude-fdatest-2026-09-06T12-00-00-000Z.md
```
**Expect:** `… not a recognisable export, skipping` → granted (appeared within 5 s on
2026-09-07). Still empty → the grant is missing or went to the wrong binary.

## 11. Obsidian  · ~3 min

Install Obsidian but **do not open the vault yet**. Copy the shipped config first,
with Obsidian closed (it rewrites both files from memory on quit): the first open
indexes `private/`'s filenames into `.obsidian/workspace.json` unless the exclusion
is already in place — it happened on the first machine.

```
mkdir -p ~/kb/.obsidian
cp ~/kb/personal/setup/obsidian-app.json ~/kb/.obsidian/app.json
cp ~/kb/personal/setup/obsidian-appearance.json ~/kb/.obsidian/appearance.json
grep -c 'private' ~/kb/.obsidian/app.json
```
**Expect:** `1` or more from the `grep`. If Obsidian is already running on the vault
picker, an absent `~/Library/Application Support/obsidian/obsidian.json` means no
vault is registered and the copy is safe.

Then **Open folder as vault** → `~/kb`. **Open `~/kb`, never `~/kb/private`.**
Opening `private` directly drops an `.obsidian/workspace.json` that records the
filenames you opened — defeating the point of numeric filenames.
**Expect:** `private/` absent from search and the file tree.

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
python3 ~/kb/base/scripts/review.py
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
| Watcher exits 0, log empty, no notes | Full Disk Access (step 10) — or granted to Homebrew's `python3` instead of `/usr/bin/python3`; run the decisive test |
| `git-crypt unlock` fails | Wrong key, or repo already unlocked |
| `base64: error decoding base64 input stream` on the key | Clipboard held the prompt line, not the 200-char base64 key (step 5 preflight) |
| `encrypted file has been tampered with` | Corrupt blob, not a wrong key — run the step-5 integrity scan, repair from history |
| Private clones present the work GitHub login | One `osxkeychain` credential per host (step 2a) |
| `private/` notes look like binary | Step 5 not done |
| Bad commit accepted | `core.hooksPath` not set (step 6) |
| Export ignored, log says "not a recognisable export" | Plain-text instead of Markdown export |
| Distillation hangs past ~5 min | Provider outage — the fallback chain is GLM → DeepSeek |
