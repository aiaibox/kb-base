# Distillation Playbook — chat exports into notes that last

What the first full pass over ~230 chat exports (2026-09-07) taught about turning
conversations into a small number of dense, correct, safe notes. `RULES.md` says
what a note must contain; this says how to get there without losing information,
duplicating it, or leaking it. Read it before any import, triage, merge or audit.

## 1. The failure modes we actually hit

| What went wrong | Why | Rule that prevents it |
|---|---|---|
| A 306-turn, three-week session was declared "unusable, nothing recoverable" | The importer's 48 KB clip kept 3 turns; the note was judged, not the export | **Never judge a session from a clipped note.** If a note says "N turns omitted", open the raw export and build a turn index first |
| Causes stated in the vault were wrong (six cases) | The distiller read the first turns; the session ruled the cause out later | **Read to the end before writing a cause.** A ruled-out cause is recorded as Rejected, not as the cause |
| Two notes for one incident; two figures for one run | Different sessions, different days, nobody compared | **Grep before you write.** One distinctive token (error string, number, command) tells you whether it exists |
| Balances, income, a medical report and holdings landed in `personal` | The chat mixed reasoning with the owner's figures | **Split reasoning from status at the sentence level.** Method → personal; figures → private, verbatim, numbered file |
| Every Gemini export was labelled "ChatGPT" | Header trusted over filename | Fixed in `watcher.py` (filename prefix wins). Verify labels at triage |
| Live S3 keys, TLS private keys, PATs, a Redis password and a kubeconfig `client-key-data` sat in raw exports | People paste configs into chats | **Reference the Secret's name or path, never the value.** List exposures for rotation in the report |
| 79 one-conversation notes on one subject each | The watcher makes one note per chat by design | **Merge first.** A subject gets one topic note; a chat adds a section |
| Coverage check by URL said 61 of 89 exports were cited | The browser exporter stamped two consecutive exports with the same URL | **Cite exports by file name and turn; a URL is a hint, not an identity** |
| `rm` aliased to `rm -i` made agents believe they had deleted files | Interactive alias in a non-interactive shell | Agents use `/bin/rm -f`; the coordinator verifies with `ls` |

## 2. Handling the source

- **Keep every raw export** somewhere durable (not `~/Downloads`). Cite it as
  `<folder>/<file>, turn N` from every note built on it. The export is the only
  route back once the note is dense.
- **Build a turn index** before reading: per turn, the user's first line and the
  reply length; group by day. It shows what the session is about, where the
  pasted logs are (user turns over ~3 KB), and which replies hold conclusions
  (code blocks, tables, "root cause / fix / verdict / because / instead").
- **Condense, never load whole.** Drop `[tool…]`, `[thinking]`, `[tool-result…]`
  lines and pasted logs (keep their first 5 lines as a hint); read the rest in
  ≤60 KB chunks. A 4 MB session becomes ~400 KB of prose.
- **Memory notes are distillations already**: trust them over a session's tail,
  keep their evidence chains verbatim, file them as incidents or reference.
- **Duplicated folders** (two copies of the same export tree) are normal; dedupe
  by session id before partitioning work.
- **Clipped imports are a smell.** The importer now clips at 2 MB; anything
  reporting omitted turns must be distilled from the export.

## 3. What to keep — the value test, sharpened

Keep: a conclusion; a verified procedure with its commands verbatim and a check
that proves it; a fact with its date and method; a decision with the options it
beat; a rejected option with the reason; a failure with its actual cause; a
question left open ("did the fix ship?" is often the most useful line); a
correction to something the vault already says.

Drop: narration, hedging, restated questions, pleasantries, tool chatter, pasted
logs, generic textbook answers, cosmetic iteration (formatting, renames), PR
prose, intermediate wrong answers — **unless** someone else would make the same
mistake; then it is a Failure with its cause.

"Not determined" is a legitimate cause. Record the evidence that exists and the
next command to run; do not invent a mechanism. When two turns give two numbers
for the same thing, keep both with dates as `> superseded …`; never silently pick.

## 4. Where it goes

- Ownership decides `personal` vs `business`, sensitivity decides `private`
  (RULES §2). Colleagues: first names, no contact details. The owner's own
  email adds nothing; leave it out.
- **Status is anything that reveals what the owner owns, owes, weighs, earns or
  plans**: balances, positions with values or cost basis, income, tax
  estimates, retirement feasibility with figures, credit score, body weight,
  medical results, a family member's medical fact, an address or phone,
  intimate or lifestyle content. It goes to `private` as a numbered file,
  verbatim, with the source URL; the reusable method from the same chat goes to
  `personal` with no figures and a one-line pointer "figures are in private".
- **Secrets** (keys, tokens, passwords, kubeconfig key material, PEMs) are
  never copied, not even into `private`. Note the Secret/ConfigMap/file that
  holds them and add the exposure to the report so the owner can rotate.
- Employer hosts, IPs and paths are fine in the employer repo; nothing from it
  is ever promoted or paraphrased into `public`.

## 5. Designing the notes — fewer, denser, correct

- **One subject, one living topic note** (plain slug; `topic` tag; sections per
  question). Captures that answer one question on their own stay dated. The
  ratio that worked: 79 chat notes → 9 topic notes plus extensions to 4.
- **Incidents are filed once and frozen**; the living index over them is a
  catalogue note (symptom → cause → fix → record). Correct an incident with a
  new incident or a catalogue row, except on the day it was filed.
- **Runbooks and project notes are living**; extend them, bump `updated:`.
- **400 lines is the soft ceiling, 600 the hard stop.** At 400, read the note end to end and split by *question* or compress; never by size: results vs how
  the knobs were chosen; running the suites vs the CI workflows around them.
  A note records conclusions, decisions, results and verified procedures —
  never the discussion; per-run history becomes one dated table or leaves.
  Leave a one-line pointer where a section moved.
- **Every figure carries its date and where it came from.** Every command is
  verbatim with a Verify line. Every source is cited to the turn.
- **Sections** (RULES §3): Scope · Conclusion · Verify · Decided · Facts ·
  Rejected · Failures · Open · References/Sources. Omit empty ones; never pad.
- Titles name the specific finding (≤60 chars). Tags are facets from
  `tags.txt`, never keywords. `created:` = the source's date, `updated:` = today.

## 6. Working with agents (what made a 230-export audit finish in an evening)

- **Partition by target-note ownership, not by source.** Each agent owns a set
  of notes it may edit and gets ≤4 MB of raw text. Anything for another note
  goes into a per-agent staging file as a ready-to-paste block headed
  `### TARGET: <repo>/<path> · <section | new note | CORRECTION>`.
- **One serial applier** merges all staging files afterwards: new notes first
  (so links resolve), then corrections, then appends; dedupes rows that two
  agents staged for the same event; splits notes at the ceiling.
- Agents never run git, never touch the raw exports, never open `private`,
  create notes only through `newnote.sh`, and end with lint clean. Their report
  is a per-file line: items found / present / added / staged / for-private /
  discarded (reason). "For private" items are filed by the coordinator.
- The coordinator rebuilds `index.md`, writes the history entry, stages, and
  keeps commits and pushes for the owner.
- Briefs that worked are in §8. Keep them with the vault so the next run does
  not rediscover them.

## 7. Before finishing — the checks

1. `python3 scripts/lint.py` clean in every repo; topic-link warnings resolved
   where a natural link exists.
2. Both inboxes empty; no `needs-review` on a finished note.
3. Coverage: every export's session id or URL is cited by at least one note, or
   its discard is recorded with a reason.
4. `grep` the vault for the status patterns of §4 and for anything that looks
   like a key; anything found moves or goes.
5. `private` was never read, listed or summarised; only written to.
6. Every note over 500 lines has a split candidate named in its Open section.
7. The history note records what changed, what was corrected, and what stayed
   unknown — an audit that finds nothing wrong is recorded too.

## 8. Reusable agent briefs (sanitised)

### 8a. Distil / merge (inbox → notes)

> Work only inside `~/kb/<repo>`. Never open `~/kb/private`. No network. No git.
> Delete consumed sources with `/bin/rm -f`. Create notes only with
> `../base/scripts/newnote.sh --tags "…" --created <source date> <path/slug>
> "<title>" <template>`; append the body under the H1 it writes; extend existing
> notes by bumping `updated:`. Tags from `tags.txt`, 1–5; wikilinks must
> resolve. One note = one question; conclusions only, never the conversation; 400 lines is
> the soft ceiling (split by question or compress), 600 the hard stop. Sections: Scope, Conclusion
> (commands verbatim), Verify, Decided, Facts (dated), Rejected, Failures, Open,
> References (each source file). Memory notes are distillations — trust them;
> raw sessions may be clipped — take what survived, invent nothing. Colleagues
> by first name; secrets by location. Report: files created / extended /
> deleted, lint line, one line per source on what was left out and why, and
> any figure that looks like status.

### 8b. Audit (raw exports → completeness)

> Read-only under the export folder. For each file: build the turn index; read
> every non-log assistant turn (all of them under ~100 KB); list durable items;
> grep the vault for each; add what is missing to the notes you own, stage the
> rest as `### TARGET:` blocks; status content is "For private" with file +
> turn, written nowhere. Where a note contradicts the export, fix (if owned) or
> stage a CORRECTION. Report per file: found / present / added / staged /
> for-private / discarded (reason). Lint clean before reporting.

## 9. Tooling changed on 2026-09-07

- `scripts/import-copilot.py`: default `--budget` 48 000 → 2 000 000 characters.
- `scripts/watcher.py`: platform label from the filename prefix when the export
  header disagrees.
- `RULES.md` §3: `volatile` is the tag alone; no frontmatter field.
- `scripts/lint.py`: warns at 400 lines, fails at 600 (`index` tag and `log/` exempt).
- `RULES.md` §4: conclusions only; soft ceiling 400, hard stop 600; merge/split quality tests.
