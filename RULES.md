# Vault rules

One copy, here in `kb-base`, which is public. Every repo's `AGENTS.md` points at
it; there are no copies to keep in step. **Edit it here** —
never edit a copy in place.

Each repo's `AGENTS.md` holds only what is specific to that repo and defers here
for everything else.

---

## 1. The one commitment

Plain Markdown in git. Every other component must pass this test: *if it
disappeared tomorrow, would I lose information, or only convenience?* If
information — reject it.

Practical consequence: a note must be useful when read as a plain text file, by a
human, with no tooling. No dependence on a plugin, a database, or a link graph.

## 2. Which repo

### The test, in one question each

| Repo | Ask yourself | Scope |
|---|---|---|
| **public** | *Would I put this on a blog?* | Knowledge **you produced** that would help a stranger: decisions with their reasoning, procedures you verified, syntheses you made. General criteria, rules and practices. |
| **personal** | *Would I show this to a friend or relative?* | **The default.** Preferences and things specific to you: hobbies, tastes, schedules, memberships, the systems you run, how you *think* about money and health. |
| **private** | *Only my spouse — or nobody?* | Secrets: actual financial status, medical status, credentials, legal matters, and lifestyle that cannot be shared. |
| **business** | *Is this about work, a client, or an employer?* | Projects, engagements, OKRs, meetings, rates, and an employer's own systems. |

These questions are the primary test. Apply them first; the ladder below only
settles cases where two of them both seem to say yes.

### Two tests for public, and both must pass

**Test 1 — nothing identifies me.** No names, employer, places I live, internal
hostnames or addresses, account details.

**Test 2 — nothing *discloses* me.** Ask: **does this reveal what I own, owe,
weigh, earn, or plan?** If yes it stays `personal`, however anonymous it reads.

The second test is the one people skip. "60% US, 25% developed international, 10%
China" contains no name — and is still *your allocation*. "300–500 kcal deficit
plus strength work" names nobody — and is still *your body*. **Absence of a name
is not absence of disclosure.**

What clears both tests is knowledge that would save a stranger real work: a
procedure you verified, a comparison carrying the options you rejected, a
corrected misconception, a public statistic you tracked down. A **distilled note
counts as produced work** — one with Verify, Rejected and References sections is
materially more than a search result. The bar excludes *bare* facts, not
distillations.

### Nothing promotes itself

`public` can only grow if something moves material into it, and no process does
that automatically — which is why it stays small while `personal` accumulates.

At triage, a note passing both tests above gets tagged **`promote-to-public`**.
A periodic sweep then **restates** each one in `public` and drops the tag.
Promotion remains a restatement, never a file move: the sanitised fact is written
fresh, and the original stays where it is.

### The line that matters most: reasoning versus status

The same subject splits across two repos depending on whether it is *how you
think* or *what is true of you*.

| Reasoning → `personal` | Actual status → `private` |
|---|---|
| how to weigh a single-country overweight | the balances in each sleeve |
| how to model a withdrawal rate | the projected portfolio total |
| how to read a DEXA result | your body-fat percentage |
| which card benefits are worth the fee | your credit limits and balances |
| how to think about a contract term | the contract you signed |

**Financial problems, not financial status. Health practices, not medical
status.** The reasoning is reusable and shareable; the numbers identify you.

### Whose information is it?

`personal` versus `business` is **not** a sensitivity question — it is an
ownership one. A colleague's name is no more secret than your own; it simply is
not yours to record.

| Material | Repo |
|---|---|
| Your CV and career history | `personal` — your history, even though it names employers |
| Your homelab Kubernetes notes | `personal`, promotable to `public` sanitised |
| Your employer's cluster configuration | `business` |
| Generic QA or Kubernetes practice you wrote up | `public` |
| A colleague's or referee's contact details | **nowhere.** You are a custodian, not an owner |

Note the ambiguity in the word *reference*: technical reference material on work
*topics* is usually `public` or `personal`; only your employer's own
configuration is `business`.

### Family follows the same rule as you

Apply the four questions to a family member exactly as you would to yourself.
General context is `personal`; actual status is `private`.

| | |
|---|---|
| `personal` | first name, life stage, which university, that they play a sport |
| `private` | full legal name with exact date of birth, medical status, and anything revealing where they are at a given time |

### The ladder, for genuine ties

Ask in order. **Stop at the first yes.** Most restrictive wins.

1. Credential, legal/medical/identity document, actual financial status, or intimate? → **private**
2. Names or concerns an employer, client, colleague, or *their* systems? → **business**
3. Specific to you or your household, but shareable with a friend? → **personal**
4. Something you produced that anyone could read forever, with nothing identifying? → **public**
5. Still unsure → **personal**.

**Never default to public.** Publication is permanent. Promotion from `personal`
is a deliberate review step where the fact is *restated* in sanitised form, not
moved. Demotion does not exist.

### Then choose the folder

Two levels maximum, and no folder is created at filing time — the sets below are
fixed, and changing them is a decision recorded in `AGENTS.md`.

**personal (10)**

| Question | Folder |
|---|---|
| Money: cards, banking, spending, tax, retirement, insurance? | `finance/` |
| A portfolio thesis, position, or standing rule? | `finance/invest/` |
| The household: house, garden, pets, auto, food, shopping? | `living/` |
| A trip, hotel, redemption, packing list? | `travel/` |
| A person — family, friend, collaborator, or your own career? | `people/` |
| Models, homelab, or the vault itself? | `tech/ai/`, `tech/infra/`, `tech/kb/` |
| Your own study, or the children's schooling? | `education/learning/`, `education/school/` |
| Training, nutrition, sport — **practice**, not status? | `health/` |
| Film, TV, music, games? | `media/` |
| A dated entry? | `log/2026/` |
| **Genuinely undecided?** | `inbox/` — triage weekly |

**public (5)** — `decisions/` · `howto/` · `notes/glossary/` · `notes/reading/`
· `research/` · `writing/`. **No `inbox/`**: this repo is pushed automatically,
so nothing may land here unreviewed.

**business (7)** — `systems/{runbooks,incidents,vendors}` · `projects/` ·
`work/` (the craft plus OKRs) · `decisions/` · `people/` ·
`log/{meetings,2026}` · `inbox/`.

**private (6)** — `finance/{accounts,tax}` ·
`identity/{documents,credentials}` · `health/` · `legal/` ·
`lifestyle/{log,notes}` · `inbox/`. Filenames are **numeric**: git-crypt hides
content, not names.

`inbox/` is a real answer, not a failure. Filing wrongly costs more than filing
late. Leaving it there past 30 days is the only unacceptable outcome.

### A missing folder from the sets above was lost, not retired

Git does not track directories. A folder that is emptied — by triage, by a
move — disappears from disk and from every fresh clone, silently. Both `inbox/`
folders in `business` and `private` vanished exactly this way.

So: **if a note belongs in one of the folders listed above and that folder is not
there, create it and file the note.** Then add a `.gitkeep` inside it, so the
next time it empties it survives. Recreating a declared folder is not inventing
one.

The opposite case is unchanged and still forbidden: **a folder outside the sets
above is never created at filing time.** If something seems to need one, it goes
to `inbox/` and the folder set is amended deliberately, in
`personal/tech/kb/kb-directory-scaffold.md`, or not at all. A folder that was
removed *because the layout dropped it* — the third-level
`finance/invest/{journal,positions,thesis,policy}`, for instance — must not
reappear; those invariants live on tags now.

## 3. How much detail — four tiers

Depth follows **durability and reuse**, never the length of the source. A
two-hour conversation may deserve four lines; a one-line decision may deserve a
page.

| Tier | Keep | Applies to |
|---|---|---|
| **Decision** | Everything needed to re-evaluate later: the context that forced it, options considered and rejected *with reasons*, the decision, its consequences, and what would reverse it | `decisions/`, `finance/invest/`, `business/systems/incidents/`, and anything tagged `decision`, `thesis` or `position` |
| **Reference** | The conclusion, the numbers, and where they came from. Drop the derivation | `notes/glossary/`, `tech/infra/`, `howto/`, and anything tagged `reference` or `benchmark` |
| **Volatile** | The figure, the date it was observed, and where to reverify. Nothing else | prices, fees, policies, availability, admissions rules |
| **Discard** | Nothing. Do not create a note — and delete one that was created | one-off lookups, filler, near-duplicates of an existing note, and **any captured exchange that reached no conclusive statement or result** — a one- or two-turn session that ends without an answer has nothing to keep |

The test for Decision tier: **would a stranger — or you in two years — understand
why, and be able to disagree?** If the reasoning is missing, the note is a
record of an outcome, not a decision.

The test for Discard: **would you ever re-read it?** If not, it is noise. An
inbox nobody reads is worse than no inbox.

### Volatile content
Tag it `volatile` and state the observation date inline next to the figure:
```markdown
GLM-5.3-Flash: $0.15/M input, $0.50/M output (observed 2026-09-05, z.ai pricing page)
```
A volatile figure with no date is worse than no figure — it will be trusted long
after it stopped being true. The tag is the only marker; there is no separate
frontmatter field.
### Captured chat conversations, specifically

> The working method — turn index, condense, read to the end, split reasoning
> from status, merge first, stage-and-apply with agents — is `docs/Distillation-Playbook.md`.
> This section says what the result must contain.

A conversation is **not** an artefact worth keeping. What was concluded is. The
transcript is discarded; only the distillation survives. The goal for every
captured note is that the solution is:

- **repeatable** — someone can re-execute it, because the exact commands and
  values are present and there is a check that proves it worked
- **traceable** — someone can verify where it came from, because every source is
  linked and every measured number carries its date and method

Use the `capture` template, or let `watcher.py` produce it automatically.

| Section | Content |
|---|---|
| **Scope** | One line: what this covers **and what it does not** |
| **Conclusion** | The answer, actionable. Commands, config and values *verbatim*, never described |
| **Verify** | The concrete check that proves it worked. **This is what makes the note repeatable** |
| **Decided** | What was committed to — only when it differs from the conclusion |
| **Facts** | Durable specifics, figures verbatim. Measured numbers carry date and method inline |
| **Rejected** | Every option considered, with the reason it lost. Prevents re-proposing |
| **Failures** | What broke and its *actual* cause. Prevents re-debugging |
| **Open** | What is unresolved. Often the most valuable line in the note |
| **References** | Every URL, service or document named, with what it was used for |

### What to leave out

- Repeated questions and repeated answers
- Greetings, sign-offs, pleasantries, and the model's own hedging
- Restating the question back
- Narration of reaching the conclusion — keep the destination, not the walk
- Generic background that could simply be looked up
- **Anything about the *conversation* rather than the *subject*.** Write "three
  options exist: A, B, C", never "we discussed three options". The conversation
  is scaffolding and comes down when the note is built.
- Intermediate wrong answers — **unless someone would independently make the
  same mistake.** Those belong in Failures. A typo does not; a misleading error
  code does.

### Two things Verify buys you

**It falsifies stale advice.** The first real test of this schema produced a note
recommending a "free, keyless, just curl it" data source. Running the generated
check showed the service now returns an anti-bot challenge — the recommendation
had silently stopped working. Without a Verify section that claim would have
entered the vault as fact.

**It surfaces missing prerequisites.** The same note added a required HTTP header
that the source conversation never mentioned. Testing confirmed the call returns
403 without it. A conclusion that omits a prerequisite is not repeatable, and only
a check reveals the omission.

### Edge cases

**No conclusion reached.** An exploratory conversation still earns a note, but it
is mostly **Open**, tagged `needs-review`, and short. It must not dress wandering
up as a finding.

**A conclusion spanning several conversations.** Update the *existing* note rather
than adding a second. Bump `updated:`. If the new position reverses the old, mark
the superseded text `> superseded by …` and keep it — per §7, the history of a
wrong belief is often the useful part.

**Held back or no summary.** If content matched a secret pattern it was never sent
anywhere, so there is nothing to distil: the full transcript is kept and tagged
`needs-review`. Same if every provider failed. Both are temporary states — distil
by hand, then delete the transcript.

## 4. Note anatomy

### Frontmatter — required, lint-enforced

```yaml
id: 01M1R7H0WBG1D3MZJVSQKT6X7M   # ULID, immutable, never edit
title: "..."                      # specific noun phrase, max ~60 chars
repo: personal                    # must match the directory
tags: [host, benchmark]           # from the repo's tags.txt, 1-5
created: 2026-09-05
updated: 2026-09-05               # bump on every edit
```

Optional, and used where they earn their place: `source:` (what import or export
it came from), `sensitivity:`, `importance:`.

### Titles

A title is the filename slug and the primary retrieval handle. Name the
**specific thing or decision**, not the topic.

- Good: `Switching from flake8 to Ruff on a 40k-line codebase`
- Bad: `Linting tools comparison`

### Size — one note, one question, conclusions only

The vault records **conclusions, decisions, results and verified procedures**.
It never records the discussion that produced them: no narration of turns, no
"we then tried", no per-run diary. A reader arrives with a question and leaves
with the answer, the check that proves it, the numbers with their dates, and the
options that lost. Length follows the number of distinct conclusions, never the
length of the source.

**Split a note when its sections are independent subjects. Do not split it when
they are steps in one sequence, however many there are.** The test: **could you
give one section a specific title and would anyone search for it on its own?**
If yes, it is a note. If it only makes sense in sequence with its neighbours, it
is a section.

**Soft ceiling: 400 lines.** A note that reaches 400 lines is stopped and read
end to end before anything is added, and one of three things happens:

1. **Split by question** — it holds more than one. Each part gets a title someone
   would search for; the parts share nothing but one pointer line each way.
2. **Compress** — it holds one question but carries derivation or history:
   prose about runs becomes one dated table; a rejected option becomes one row;
   a timeline stays only in an incident; repeated facts collapse to one line
   with both dates when they disagree (`> superseded`).
3. **Justify** — it is an index over other notes (`topic`) or an append-only log
   (`log/`, the history note). Even then it links out rather than inlining.

**Hard ceiling: 600 lines** — the embedding window; past it the tail becomes
unfindable. Lint warns at 400 and fails at 600; only `index`-tagged notes and
`log/` are exempt.

**After a merge the note must be shorter than the sum of its sources** — the
overlap was the point. **After a split each part must read as a complete note**
with its own Scope, Conclusion and Verify, not as "part 2 of". If a merge or a
split does not leave the reader better off than the originals, it was the wrong
operation.

### How to merge

1. **Pick the target, never create one.** The living note on that subject wins:
   the `topic` note, else the oldest note that already answers the question. It
   keeps its `id` and its filename; a merge never mints a new note. If no note
   answers the question yet, the *first* source becomes the target and is
   renamed to a plain slug.
2. **Decide the section order from the reader's path**, not from the sources'
   dates: what the answer is, how to check it, what the numbers are, what lost,
   what broke, what is open. One `## Sources` list at the end.
3. **Fold, do not append.** Each source's Conclusion joins the target's
   Conclusion or becomes one row in a decisions table; its Verify checks join
   the Verify block if they still make sense; its Facts, Rejected and Failures
   merge into the target's, deduped. Never leave a source's Scope boilerplate,
   footer or "distilled from an N-turn conversation" line.
4. **Conflicts are dated, not resolved by choice.** When two sources disagree,
   the later reading is the current text and the earlier stays inline as
   `> superseded 2026-09-06: …`. Two measurements of the same run keep both with
   their dates and methods.
5. **Dates and tags:** `created:` becomes the earliest source's date, `updated:`
   today. Tags are the union, trimmed to five by dropping the least
   discriminating; add `topic` once the note gathers three or more others.
6. **Repoint, then delete.** Grep every repo for each consumed slug and repoint
   the wikilinks and index entries at the target *before* deleting the source.
   Consumed sources are deleted, never left as stubs or redirects — git holds
   the history.

### How to split

1. **Cut on the question boundary**, never at a line count. Name each part by
   the question it answers; if you cannot name it in a searchable title, it is a
   section and the cut is wrong.
2. **The original keeps its `id`** and becomes either the shortest part or a map
   over the parts. New parts come from `newnote.sh` with `created:` set to the
   earliest date of the material they carry.
3. **Each part is whole:** its own Scope, Conclusion, Verify, Facts, Open and
   Sources for the material it holds. No "continued from", no shared preamble.
4. **One pointer line each way**, and nothing else duplicated: a figure, table
   or command appears in exactly one part.
5. **Repoint every inbound link** and both index entries; a split that leaves a
   dangling `[[slug]]` has not happened yet (lint will say so).
6. **Delete the scaffolding.** Sentences about the note's own size ("moved here
   to stay under the ceiling") are false the moment the split lands.

### When not to merge

- **A frozen record.** `business/systems/incidents/` and anything past sign-off
  is corrected by a new note or a catalogue row, never by folding it into
  something else. Same for append-only logs.
- **Across a repo boundary.** Two notes on one subject in different repos are a
  sensitivity split (RULES §2), not a duplicate. Restate what each side needs.
- **A note that fails the value test.** Delete it; do not dilute a good note
  with it.
- **A title coincidence.** The weekly digest's merge candidates share words, not
  questions. They are candidates for a human decision, and the answer is often
  "no, these are two questions".

### Creating notes

```
../base/scripts/newnote.sh <path/slug> "<title>" [template]     # run inside the target repo
```

**This is the only correct way.** It generates the ULID. Writing a note file
directly means inventing an `id`, and lint will reject it. An agent that cannot
run the script should output the content and let a human create the note.

## 5. Tags

The principle: **tag only what full-text search cannot find.**

A note mentioning Chase is already findable by searching `Chase`. A note that
*is a decision* is not — nothing in its text says so. So `decision` is a useful
tag and `chase` is not.

Consequences:
- Tags are **facets**, not keywords. Domain, note type, and status.
- Specific entities — people, companies, tickers, product names, places — belong
  in the title and body, never in tags.
- One controlled vocabulary, `base/tags.txt`, enforced by lint in every repo. Adding a
  tag is a deliberate edit to that file, not something done in passing.
- 1–5 tags. A note needing more than five has not been split.
- English only, like every other artifact in this vault.
- **Adding a tag to a note already at five means dropping one deliberately.**
  Never truncate — a script that appends then trims silently discards the tag it
  was asked to add.

### Two tags carry the weight of a whole tier

Atomic notes each record a decision *at a time*. Nothing inside them says which
decision is now true, and that gap is closed by two tags rather than by a folder:

- **`superseded`** — this note is no longer current. Use it when one decision
  genuinely replaces another. Drop `volatile` at the same time: a dead note does
  not belong in the re-verify pool.
- **`topic`** — this note synthesises others into the current picture: a map, an
  aggregate across sleeves, a "what am I actually doing now". It lives in its own
  domain folder like any other note, so the tier adds no folder and no third
  level. Lint **warns** (never blocks) if it links fewer than three notes, since
  a topic note is often written before the notes it will gather.

Reach for `superseded` when one note replaces another, and `topic` when no single
note can hold the answer.

## 6. Links

`[[slug]]`, and **only to notes inside the same repo**. Lint enforces this.

Cross-repo links are forbidden by design. To use something from a more private
repo in a more public one, restate the sanitised fact. The friction is the point:
it forces a conscious decision at the moment of disclosure.

Inline code is exempt, so documentation can write `[[slug]]` as an example.

## 7. Append, supersede, retain

- **Append-only:** `log/`, `tech/kb/kb-history.md`, and any investment journal
  entry. Never retroactively edit. Git enforces nothing here; `merge=union` in
  `.gitattributes` only stops a merge from silently dropping lines, and that
  rule is inert unless its path matches the live layout.
- **Frozen after sign-off:** `business/systems/incidents/`. Correct the record
  in a new note.
- **Merge first.** Before writing a new note, search for the one that already
  answers the question — `kbs`, the topic notes, the weekly digest's merge
  candidates — and fold the new material into it, bumping `updated:`. Adjacent
  questions on one subject belong in **one readable note with sections**, not in
  several thin siblings; when the combined note no longer fits a screen or two,
  that is what a `topic` note is for. Fewer, denser notes search better than many
  small ones. Merging is the default; a new note is the exception that needs a
  reason. The digest's candidates share title words, not questions — they are a
  prompt to decide, not an instruction to merge. **How** to merge and split, and
  when not to, is §4.
- **Value test before anything is kept.** Ask: *will this be worth finding in a
  year?* A note that records a conclusion, a decision, a verified procedure, a
  number with its date, or a rejected option with its reason passes. A note that
  records only that a conversation happened — no result, no decision, nothing
  reusable — fails, and is **deleted**, not superseded. Short captures fail this
  test most often.
- **Supersede a belief; delete a nothing.** When a note recorded something that
  was believed and later revised, mark it `> superseded by [[slug]]` and leave
  it — the history of a wrong belief is often the useful part. When a note never
  had future-reference value, delete it. **Supersession is for notes only.**
  Scripts, docs, templates and config are tools, not records — when one is
  redundant, delete it. See `WORKING-RULES.md` §7.
- **`inbox/` is the only unstructured folder.** Triage weekly. An item older than
  30 days is either filed or deleted — never left to rot.
- **Volatile notes** whose observation date is over a year old are reverified or
  marked superseded.

## 8. Secrets

Reference a secret's location, never its value: "Bitwarden → kb-private
git-crypt key". No exceptions, in any repo. Git history is permanent — a value
committed once is committed forever, and rewriting history is unreliable.

## 9. Before finishing

```
python3 scripts/lint.py
```

The pre-commit hook runs it and refuses the commit on failure. `--no-verify`
exists for genuine emergencies and is not one of them.
