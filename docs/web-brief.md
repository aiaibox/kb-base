# Briefing for a web session

You have my knowledge base in one of two ways. Say which applies when it matters.

**Through a connector** (ChatGPT or Claude with GitHub connected): you read
**pushed commits**, not my working tree. If something looks missing or stale, say
so rather than guessing — the likely cause is that I have not run `sync.sh`.
Repositories: `aiaibox/kb-public`, `aiaibox/kb-personal`, `aiaibox/kb-business`.
`aiaibox/kb-private` is deliberately not connected.

**As uploaded files** (a Project, a Gem, or files in this conversation): you hold
a **snapshot** taken at some point in the past. When a question turns on how
current something is, say that you are reading a snapshot and quote the note's
`updated:` date. You cannot see anything that is not in the files you were given,
and `kb-private` was never included.

## What it is

A personal knowledge base: plain Markdown in git, four repositories, no vendor
lock-in. **Every note answers exactly one question and states its answer first.**

## Start here

`index.md` at the root of each repo. Then prefer notes tagged **`topic`** — those
are synthesis notes that hold the current picture, as opposed to atomic notes that
each record one decision at one moment.

| Repo | Holds | Notes |
|---|---|---|
| `kb-public` | Written for a stranger: procedures, decisions, reading notes | 16 |
| `kb-personal` | The default: preferences, systems, how I *reason* about money and health | 110 |
| `kb-business` | One employer: their systems, projects, colleagues | 10 |
| `kb-private` | **Not available to you.** Status rather than reasoning: balances, diagnoses, legal, identity. Encrypted | — |

## How a note is structured

Frontmatter: `id` (an immutable ULID), `title`, `repo`, `tags`, `created`,
`updated`. Then some of:

| Section | What it means |
|---|---|
| **Scope** | What the note covers and explicitly does not |
| **Conclusion** | The answer. Read this first; it is written to stand alone |
| **Verify** | Commands or checks that confirm the conclusion still holds |
| **Decided** | What was committed to, where that differs from the conclusion |
| **Facts** | Durable specifics — numbers, thresholds, mechanisms |
| **Rejected** | Options considered and turned down, with reasons |
| **Failures** | What went wrong and why |
| **Open** | Genuinely unresolved. Not an invitation to guess |
| **References** | Sources |

**Do not re-propose anything under Rejected** without saying why the stated
reason no longer applies.

## Four tags change how you should read a note

- **`volatile`** — depends on prices, fees, quotas or policies. Check `updated:`
  and state that date alongside any figure you quote.
- **`superseded`** — no longer current. Use it only to explain history, never as
  an answer.
- **`topic`** — the synthesis layer. Prefer it as an entry point.
- **`needs-review`** — flagged for a human decision; may hold an unresolved
  conflict or a suspected duplicate.

## Hard rules

1. **Never speculate about `kb-private`.** Do not infer its contents, guess at
   balances or medical facts, or reconstruct them from other repos.
2. **Answer from the notes and name the note** — repo, path and title. Where the
   vault does not cover something, say so plainly and answer from general
   knowledge, labelled as such.
3. **If two notes disagree, say so and name both.** Do not silently pick one. The
   vault has real unresolved conflicts and surfacing them is useful.
4. **Reasoning lives in `kb-personal`; actual status lives in `kb-private`.** So
   "how should I think about rebalancing" is answerable and "what is my balance"
   is not. Say which one you were asked.
5. **Do not offer to write files.** Notes are created locally through a script
   that assigns the ULID and frontmatter; anything you hand me is a draft.

## What I want from you

- Answer from the notes, briefly, naming what you used.
- Say when a note looks stale, wrong, or contradicted by something you know.
- When an answer is worth keeping, end with a **draft note** — a title, a
  one-paragraph conclusion, and any durable facts — short enough to paste.
