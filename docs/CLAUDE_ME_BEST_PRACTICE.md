# CLAUDE.md best practices — six sources, one synthesis

What to put in `CLAUDE.md` / `AGENTS.md`, how Claude Code actually consumes
those files, and where the published advice agrees, disagrees, or is wrong.
Points made by more than one source are merged into one statement with every
source tagged; points made by one source stand alone; genuine conflicts are
described, not averaged. The official Claude Code documentation is used as the
arbiter for mechanics only, and is tagged separately.

| Tag | Source | Read |
|---|---|---|
| **[BC]** | buildcamp, *The Ultimate Guide to CLAUDE.md in 2026* — buildcamp.io/guides/the-ultimate-guide-to-claudemd | 2026-09-17 |
| **[CCBP]** | MuhammadUsmanGM/claude-code-best-practices, v1.7 (2026-09-15) — whole repo: README, 40 guides, 11 templates, 5 starter kits, tools, plugins, dogfood `.claude/` | 2026-09-17 |
| **[TAI]** | towardsai / AI Unfiltered, *CLAUDE.md Best Practices* (2026-05-06) — pub.towardsai.net/claude-md-best-practices-13cfe020050d | pasted text |
| **[12FA]** | humanlayer/12-factor-agents @ d20c728 — README, `content/` (12 factors + appendix), `drafts/`, `workshops/`, both `CLAUDE.md` files | 2026-09-17 |
| **[HL]** | HumanLayer, *Writing a good CLAUDE.md* — humanlayer.dev/blog/writing-a-good-claude-md | 2026-09-17 |
| **[BTN]** | buildthisnow, *CLAUDE.md Best Practices* — buildthisnow.com/blog/tools/claude-md-best-practices | 2026-09-17 |
| **[Docs]** | Claude Code documentation, *How Claude remembers your project* — code.claude.com/docs/en/memory | 2026-09-17 |

**The one-paragraph version.** The file is the highest-leverage prompt you
own, delivered as an advisory user message, not as enforced configuration. It
competes for a budget of roughly 100–150 instructions with everything else in
the session, so it should hold only what is true in every session, stated
concretely enough to verify, with the reason attached where a rule has edge
cases. Everything else moves out: deterministic checks to hooks and
permissions, procedures to skills, path-specific rules to `.claude/rules/`,
deep reference to files the agent is pointed at and reads on demand. Write it
by hand, grow it from real mistakes, keep the root under about 200 lines, and
test that it loaded and is being followed.

---

## 1. What the file is, and why every line matters

**Merged view — all sources.** An LLM is a stateless function: it knows
nothing about your project except the tokens you give it, and every session
starts from zero **[HL] [12FA]**. `CLAUDE.md` is the mechanism that delivers
that missing context at the start of every conversation **[HL] [BC] [CCBP]
[Docs]** — "the place you write down what you'd otherwise re-explain"
**[Docs]**, "a briefing document" **[CCBP]**, "an onboarding document that
prevents repetition across conversations" **[BC]**.

**It sits at the top of a leverage hierarchy.** Bad research documents
produce bad plans, bad plans produce bad code, and all of them inherit from
`CLAUDE.md`; "a bad line in your CLAUDE.md creates bad lines across every
single task" **[BC] [HL]**. This is the reason both give for hand-crafting
every line.

**It is your prompt, so own it.** Twelve-Factor's Factor 2 ("own your
prompts") and Factor 3 ("own your context window") are the general form of
the same idea: don't outsource prompt engineering to a black box; treat
prompts as first-class code you can test, evaluate, iterate and read;
"everything is context engineering" and "the context window is your primary
interface with the LLM" **[12FA]**. In Claude Code the harness owns the system
prompt and the tool schemas; `CLAUDE.md`, `.claude/rules/`, skills and
`--append-system-prompt` are the parts of the prompt you own.

**It pays for itself quickly, but not instantly.** The only measured numbers
come from **[CCBP]**'s benchmark harness (Sonnet 4.6, April 2026, three
tasks): no `CLAUDE.md` 78 200 session input tokens; a 30-line file 76 900
(−1.7 %); a 180-line file 71 400 (−8.7 %). The first turn costs ~600 extra
input tokens; every later turn saves 1.5–3× that in avoided exploration, so
break-even is 2–4 turns **[CCBP]**. Independently, **[BTN]** cites a February
2026 ETH Zurich study on 300 SWE-bench Lite tasks: human-written files
improved task success by about 4 %, auto-generated ones cut it by about 3 %.

**It also applies to `AGENTS.md`.** The advice is tool-agnostic **[HL]**.
Claude Code itself reads only `CLAUDE.md`; to share one file with other
agents, either `@AGENTS.md` from a tiny `CLAUDE.md` or symlink
`CLAUDE.md -> AGENTS.md` (symlink needs admin rights on Windows) **[Docs]**.

---

## 2. How Claude actually consumes it — the mechanics that decide everything

These facts explain most of the advice in later sections. Where a source
contradicts the documentation, the documentation wins and the conflict is
noted.

### 2.1 It is advisory, delivered as a user message

* Content is injected **as a user message after the system prompt**, "the
  same kind of message you type" — not system-level, not enforced **[BTN]
  [Docs] [HL]**. Claude "treats them as context, not enforced configuration"
  **[Docs]**.
* The harness wraps it in a reminder that the context "may or may not be
  relevant to your tasks … you should not respond to this context unless it
  is highly relevant" **[HL]**. Consequence: instructions that are not
  universally applicable get deprioritised. **[HL]** speculates Anthropic added
  this because people used the file as a dump of non-generalisable hotfixes.
* **[BTN]** reports compliance falling from above 95 % at the start of a
  session to 20–60 % by message six to ten, and links it to the
  "lost-in-the-middle" effect (over 30 % accuracy drop on buried
  instructions). No source for the numbers is given in the article; treat them
  as a claim, but the direction matches **[HL]**'s and **[BC]**'s budget
  argument.
* To *block* something regardless of what the model decides, use a
  `PreToolUse` hook or `permissions.deny`; for instructions that must live at
  system-prompt level, use `--append-system-prompt` at launch **[Docs]**. See
  §8.

### 2.2 What loads, when, and in what order

| Location | Scope | Loads | Shared | Source |
|---|---|---|---|---|
| Managed policy file (`/Library/Application Support/ClaudeCode/CLAUDE.md`, `/etc/claude-code/CLAUDE.md`, …) or `claudeMd` key in managed settings | whole machine | at launch, first; cannot be excluded | all users | [Docs] |
| `~/.claude/CLAUDE.md` | all your projects | at launch | you | [BC] [CCBP] [Docs] |
| `~/.claude/rules/*.md` | all your projects | at launch, before project rules | you | [Docs] |
| `./CLAUDE.md` or `./.claude/CLAUDE.md`, plus every ancestor directory's | project | at launch, root-most first, cwd last | team via git | [BC] [CCBP] [Docs] |
| `./CLAUDE.local.md` | project, personal | at launch, after the `CLAUDE.md` beside it; gitignore it | you | [BC] [Docs] |
| `./.claude/rules/*.md` (recursive) without `paths:` | project | at launch, same priority as `.claude/CLAUDE.md` | team | [BC] [BTN] [Docs] |
| `./.claude/rules/*.md` with `paths:` frontmatter | matching files | when Claude reads a matching file | team | [BC] [BTN] [Docs] |
| `./subdir/CLAUDE.md` | subtree | **on demand**, when Claude reads files there | team | [BC] [CCBP] [Docs] |

* All discovered files are **concatenated**, not overridden; files nearer the
  working directory are simply read later **[Docs]**. **Conflict:** **[CCBP]**
  (claude-md-guide, custom-instructions) says "more specific files take
  precedence" / "later files take precedence, so directory-level instructions
  override project-level ones". There is no override; two contradictory
  instructions just both load and "Claude may pick one arbitrarily" **[Docs]**.
* Start Claude in the repo you mean to work in: only the cwd's ancestors load
  at launch; sibling and child directories do not **[Docs]**.
* `claudeMdExcludes` (glob on absolute paths, any settings layer) skips
  other teams' files in a monorepo; managed files cannot be excluded **[Docs]**.
* A file over 4 MiB is skipped entirely **[Docs]**.
* After `/compact`, the project-root `CLAUDE.md` is re-read from disk and
  re-injected; nested files and `paths:` rules reload when a matching file is
  read again **[Docs]**. **Conflict:** **[CCBP]** troubleshooting says "a very
  long conversation may push CLAUDE.md context out of the active window" —
  not so for the root file; only conversation-given instructions are lost.

### 2.3 Imports, comments and other syntax

* `@path/to/file` imports the file **at launch**, expanded in place; relative
  paths resolve against the importing file; recursion allowed to a depth of
  **four** hops **[Docs]**. **Conflict:** **[BC]** says "up to 5 levels".
* Imports **do not save context**: "imports cut visual clutter but do not cut
  total token cost" **[BTN]**; "imported files still load and enter the
  context window at launch" **[Docs]**. This matters for §7.
* Import parsing skips code spans and fenced blocks — write `` `@README` ``
  to mention a path without importing it **[Docs]**.
* An import that resolves outside the working directory (e.g. `@~/…`) is
  *external*: a one-time approval dialog appears for project files; user-scope
  files are trusted **[Docs]**.
* **Block-level HTML comments are stripped before injection** — notes for
  maintainers cost zero tokens; comments inside code blocks are preserved
  **[BTN] [Docs]**. The **[CCBP]** starter kits use `<!-- edit -->` markers
  this way.
* `.claude/rules/` `paths:` accepts globs and brace expansion
  (`src/**/*.{ts,tsx}`), one budget of 1 000 expanded patterns per rule
  **[Docs]**; rules without `paths` load unconditionally **[BC] [Docs]**.
* Symlinked rule directories work; a symlink target outside the working
  directory is treated as an external import **[Docs]**.

### 2.4 The commands that let you see what happened

`/context` lists the memory files that actually loaded (the only proof a
file was read) **[Docs]**; `/memory` opens and creates them and toggles auto
memory **[Docs]**; `/doctor` (v2.1.206+) proposes trims for content Claude can
derive itself **[Docs]**; `/init` generates or improves a file (see §10 for the
disagreement about using it) **[Docs] [CCBP]**; the `InstructionsLoaded` hook
logs which instruction files loaded, when and why — the way to debug
`paths:` rules **[Docs]**.

### 2.5 Auto memory is a separate channel

`~/.claude/projects/<project>/memory/MEMORY.md` — the first 200 lines or
25 KB load every session, topic files load on demand; Claude writes it, you
write `CLAUDE.md` **[BC] [BTN] [Docs]**. **[BTN]**'s division of labour:
`CLAUDE.md` for "stable conventions you curate by hand", `MEMORY.md` for
"things it discovers". Claude skips saving anything derivable from the code or
already in `CLAUDE.md` **[Docs]**.

---

## 3. The instruction budget and the length rule

**Merged view.** Frontier models follow roughly **150–200 instructions** with
reasonable consistency; Claude Code's own system prompt already spends about
**50**, leaving **100–150** for everything you add **[HL] [BC] [BTN]**. As
the count rises, performance degrades **uniformly across all instructions**
— the model does not drop the newest ones, it starts ignoring all of them a
little **[HL] [BC]**. Smaller models degrade exponentially, larger thinking
models roughly linearly **[HL] [BC]**. Models are biased toward instructions
at the periphery of the prompt **[BC] [BTN]**. Twelve-Factor states the same
law for the whole context: "as context grows, LLMs are more likely to get lost
or lose focus"; keep an agent's job to "3–10, maybe 20 steps max" **[12FA]**.

All three articles present the 150–200 figure as "research indicates" without
citing the study. Treat the number as an order of magnitude, not a
specification — the *uniform degradation* claim is what changes how you
write.

**Practical consequence:** count instructions, not lines. A 60-line file of
dense imperatives can hold 80 instructions; a 200-line file of headings and
pointers can hold 30.

### Where the sources put the line-count ceiling

| Source | Ceiling | Notes |
|---|---|---|
| [Docs] | **under 200 lines** per file | "Longer files consume more context and reduce adherence" |
| [BTN] | under 200 "official"; under **60** for high-signal teams; past ~300 "compliance drops and costs climb with no real gain" | |
| [CCBP] | under 200 (linter warns above 200 and below 10); 40–80 for a monorepo root, 20–40 per package; quickstart prompt asks for under 60; minimal example is 20 lines | starter kits ~100 lines each |
| [HL] | under **300**, shorter is better; their own root is under 60 | |
| [BC] | under 300, ideally under 100; 60 for high-performing teams | checklist: "Under 300 lines (ideally under 100)" |
| [12FA] | no line figure; "small, focused agents" | |

**Difference described:** the ceilings range from 60 to 300, but they are not
in conflict once you separate *root file* from *total loaded*: the 60-line
figures are the hand-curated root that every session pays for; the 200–300
figures are the tolerable total. Only **[CCBP]**'s own benchmark measured a
180-line file and found it still net-positive after three turns, which is the
one data point supporting the higher ceiling. A defensible rule: **root under
~100 lines, everything that loads at launch under ~200 lines, and never past
300**.

---

## 4. What belongs in the file

### 4.1 The WHAT / WHY / HOW frame

**[HL]** and **[BC]** organise content around three questions, and every other
source's "include" list fits inside them:

* **WHAT — the project map.** Tech stack, runtime and package manager; the
  project structure, "especially important in monorepos" — which apps exist,
  what the shared packages do — "so the agent knows where to look for things"
  **[HL] [BC]**. "Where the important stuff lives: entry points, the main
  config file, the folder that holds business logic" **[BTN]**. **[CCBP]**'s
  linter warns when there is no Architecture section, and its templates give
  one line per top-level directory ("`src/routes/` — API route handlers").
* **WHY — purpose and rationale.** What the project does, what each
  component is for, the reasoning behind architectural decisions, so Claude
  "makes better judgment calls" **[HL] [BC]**. Twelve-Factor's framing: give
  the model the edges of the graph and let it choose the path — that only
  works if it knows what the graph is for **[12FA]**.
* **HOW — working on the project.** Exact build, test, lint, type-check and
  run commands; tooling preferences ("use `bun`, not `node`"); how to verify a
  change after making it **[HL] [BC] [BTN] [CCBP]**. **[CCBP]**'s linter makes
  a Commands section the one *required* section (error, not warning), asks for
  commands in backticks so they are copy-pasteable, and every template lists
  the **single-test** invocation because "the syntax varies across test
  runners". Include the "run X before committing" line **[CCBP]** (all
  templates, dogfood file).

### 4.2 Constraints and conventions that break defaults

* "Conventions that break common defaults. If your team does something
  unusual, say so" and "hard constraints — 'never use the service role key in
  client code'" **[BTN]**. `/doctor` keeps exactly this class: "pitfalls,
  rationale, and conventions that differ from tool defaults" **[Docs]**.
* A guardrails section — `## Do NOT`, `## Rules` or `## Constraints` — is
  what **[CCBP]**'s linter looks for; every template ends with one. Typical
  entries: never edit generated files; no dependencies without asking; no raw
  SQL; no `unwrap()` outside tests; never trust a client-supplied user id.
  The template commentary is explicit about *why* these earn a line: they
  "prevent Claude from reaching for older patterns it may have learned from
  training data" and catch mistakes the model "would otherwise use freely".
* Known gotchas and legacy patterns to avoid; testing patterns; required
  environment variables or services; PR and commit conventions **[CCBP]**.
* Cloud and infrastructure context — provider, region, IaC location, CLI
  tools available — when the project touches them **[CCBP]**.

### 4.3 Who the output is for

**[TAI]**'s distinctive contribution, missing from every other source: almost
no `CLAUDE.md` says who the *audience* is. "Claude is almost never writing for
you. It's writing for your users, your teammates, your reviewers, or your
future self six months from now." One paragraph naming the readers of code
reviews versus documentation, and what each needs, "generates the biggest
improvement with the least effort".

### 4.4 Values, intent, edge-case reasoning — the "constitution"

**[TAI]**'s thesis: a "config-file" `CLAUDE.md` (a bullet list of
preferences) works until the situation is not covered by a rule, "and then it
just guesses". A "constitutional" one adds three things a config never has:

* **Values** — the *why* behind each decision, so the model can generalise.
* **Intent** — what success looks like in your context.
* **Edge-case reasoning** — what to do when two things it knows about you
  point in opposite directions; **tradeoff statements** such as "speed
  matters in this codebase, but not more than someone understanding what
  they're looking at".

The test before adding anything: "if you couldn't see the output and had to
describe what you'd want Claude to be thinking about right now, what would you
say? … If you're describing an output state instead of a thinking process,
rewrite it." One-sentence version: "a CLAUDE.md that tells Claude what to
value is more useful than one that tells it what to do, because values
generalize and rules don't." Success is measured not in output quality but in
**fewer follow-up corrections** **[TAI]**. The convergent point from the other
side: **[CCBP]**'s AP-1 fix gives each concrete rule "the why for each", and
**[Docs]**' consistency rule exists because two unexplained rules that
conflict get resolved arbitrarily.

### 4.5 When to add a line

Add to the file when Claude makes the same mistake **a second time**, when a
code review catches something Claude should have known about this codebase,
when you type the same correction you typed last session, or when a new
teammate would need the same context **[Docs]**. "Expand your CLAUDE.md when
you notice Claude using the wrong style repeatedly, putting files in the wrong
directory, missing a convention that matters, or suggesting libraries you have
decided against … add one or two lines to address the specific issue. A
CLAUDE.md that grows organically from real problems is more useful than one
written speculatively" **[CCBP]**.

---

## 5. What to keep out

Every exclusion below is a budget decision: the line costs an instruction in
every session and buys nothing there.

| Exclude | Why | Where it goes instead | Sources |
|---|---|---|---|
| **Code style and formatting rules** | "Never send an LLM to do a linter's job": LLMs are expensive, slow and in-context learners — they pick the style up from the code they read; style rules "bloat context windows and degrade performance" | a formatter/linter run from a `Stop` or `PostToolUse` hook (Biome, Prettier, ruff, gofmt); or a slash command that formats what changed | [HL] [BC] [BTN] |
| **Anything derivable from the repo** | "The technology stack (Claude can read `package.json`)"; "don't document things Claude can figure out by reading your code" | nowhere — `/doctor` cuts "directory layouts, dependency lists, and architecture overviews" | [BTN] [CCBP] [Docs] |
| **Task-specific instructions** | "how to structure a new database schema" is irrelevant to most sessions and dilutes universal rules | a skill, a slash command, or a `paths:`-scoped rule | [HL] [BC] [Docs] |
| **Hotfixes for a single misbehaviour** | "If Claude misbehaves once, resist adding rules. Find systematic solutions" — the file is where hotfixes go to die and is why the harness now down-weights it | a hook if it must never happen; wait for the second occurrence otherwise | [BC] [HL] [Docs] |
| **Generic wisdom** | "Write clean code", "follow best practices", "be careful with the database" — "not an instruction, it's a mood"; wastes budget | delete; the linter flags these phrases | [BC] [CCBP] |
| **Empty or outline-only sections** | tokens that say nothing and make the file look complete | delete until there is content | [CCBP] |
| **Model IDs** | they rotate; a retired ID cannot be run | describe the selection criterion ("current Sonnet for most work, Opus for plan mode") | [CCBP] |
| **Absolute paths from one laptop** | teammates read a fictitious map; paths leak into PRs | repo-relative paths | [CCBP] |
| **Secrets, or examples that look real** | the file is committed; a leaked key must be rotated | name the env var and where the real value lives ("in 1Password under …") | [CCBP] and §9 |
| **The whole directory tree, or copies of README content** | too long, changes constantly, duplicates what exists | one line per directory that matters; a pointer to README | [CCBP] |
| **Code snippets** | "will become out-of-date quickly" | `file:line` pointers — "prefer pointers to copies" | [HL] [BC] |
| **A single monolith covering every package** | 600 lines, six H1s, contradictory test commands; everyone pays for tokens they don't need | one file per package; the root holds only cross-cutting rules | [CCBP] |
| **Bare rule lists with no why** | they "collapse the instant Claude hits an edge case" | attach the value or tradeoff the rule protects | [TAI] |

**Difference described — code style.** **[HL]**, **[BC]** and **[BTN]** say
style rules never belong in the file. **[CCBP]** disagrees in practice: its
eleven templates and its custom-instructions guide carry extensive style
sections ("Maximum function length: 30 lines", "name boolean variables with
is/has/should prefixes", named-vs-default exports, props naming). The
reconciliation is the one **[BTN]** gives: a convention **that breaks the
default** and that no formatter enforces (no default exports; typed IDs, not
strings; services never import HTTP types) is a constraint and earns a line;
anything a linter *can* check should be checked by the linter and removed from
the prompt.

**Difference described — the project map.** **[BC]**, **[HL]** and **[CCBP]**
want a WHAT section; **[BTN]** and `/doctor` **[Docs]** cut "architecture
overviews" as derivable. Both are right about different things: a directory
listing is derivable and should go; *which* of three apps in a monorepo is the
one to change, and *why* a package exists, is not derivable from a tree and
should stay.

---

## 6. How to write it — form, tone, emphasis

### 6.1 Specific enough to verify

"Use 2-space indentation" not "format code properly"; "run `npm test` before
committing" not "test your changes"; "API handlers live in `src/api/handlers/`"
not "keep files organized" **[Docs]**. "'Use `vitest` for tests' is better
than 'we have tests'" **[CCBP]**. The fixed version of AP-1 gives "four concrete
actions and the why for each" **[CCBP]**. **[12FA]**'s Factor 4 is the
general principle: the model's job is to emit a structured decision your code
can act on; a vague instruction produces a vague decision.

### 6.2 Bullets and headers — or prose?

* **[Docs]** and **[CCBP]**: "use markdown headers and bullets to group
  related instructions. Claude scans structure the same way readers do";
  "bullet points are easier for Claude to parse than long paragraphs";
  "writing essays instead of actionable bullet points" is an anti-pattern.
  **[CCBP]**'s dogfood style guide: "lead with the answer", tables for
  comparisons, "no filler, no hedging".
* **[TAI]**: the rewritten example is deliberately "no bullet points, no
  'don't do X', just intent, context, and reasoning", because a paragraph can
  hold a tradeoff and a bullet cannot.

**Difference described.** These are answers to different questions.
Commands, paths and hard constraints are look-up items and belong in bullets
and tables. Values, audience and tradeoffs are reasoning and read better as
two or three sentences. The failure mode is applying either form to the other
kind of content: a bulleted "Tone: professional" **[TAI]**'s central example of
what breaks — or a paragraph that buries the test command.

### 6.3 State the why — but in one clause

Every source that discusses adherence wants the reason attached: **[TAI]**
(values), **[HL]** and **[BC]** (the WHY of WHY/WHAT/HOW), **[CCBP]** AP-1
("the why for each"), **[Docs]** (conflicting rules are picked arbitrarily —
the reason is what lets the model rank them). The budget argument of §3 is the
counter-pressure: an explanation is more tokens. The practical compromise
visible in the best examples — "Never edit files in `internal/store/` — they
are overwritten by sqlc" **[CCBP]**; "we use named exports because they make
large-scale refactoring cleaner" **[TAI]** — is a rule plus a one-clause
reason, and the reason is only written where the rule has an edge case.

### 6.4 Positive over negative, yet keep a Do-NOT section

**[CCBP]**'s custom-instructions guide: "State what to do, not just what to
avoid — positive instructions are clearer than negative ones" ("Use Zod
schemas for all API input validation" beats "Don't use manual validation").
The same repo's linter wants a `## Do NOT` section and every template has one.
The tension resolves on content: a prohibition earns its place when the
positive form has no natural home ("Do not edit `db/schema.rb` manually",
"Do not use `setState` for data that could be in a provider"); a preference
between two valid options is better stated positively.

### 6.5 Position and emphasis

* Put the most important rules **at the top and the bottom, never the
  middle** **[BTN]**; "place the most important rules at the top — Claude
  weighs earlier content more heavily" **[CCBP]**; models attend to
  "instructions at prompt peripheries" **[BC]**.
* Emphasis is a scarce resource. The counter-example is **[12FA]**'s own
  `CLAUDE.md`, a promptx-generated persona router: "🚨 MANDATORY PERSONA
  SELECTION", "CRITICAL: You MUST adopt one of the specialized personas before
  proceeding", "DO NOT PROCEED WITHOUT SELECTING A PERSONA", "READ FIRST:
  Always read at least 1500 lines", "COMMIT FREQUENTLY: every 5–10 minutes",
  repeated in a "CRITICAL REMINDER" at the end. When every line shouts, no line
  stands out, and the uniform-degradation finding of §3 says the extra
  instructions cost adherence on the ones that matter. Its workshop
  `CLAUDE.md` — plain bullets of tools, commands, learnings and pitfalls — is
  the shape the other sources recommend. (The persona file is also in the
  repo's own words a template "to copy or merge", not a description of how
  the authors write prompts; their Factor 2 example prompt is measured and
  specific.)

### 6.6 Examples anchor abstractions

Short examples — a commit message, a handler signature, an error-wrapping
line — "anchor abstract instructions" **[CCBP]**; the templates' commentary
credits the Rust `AppError` and Django `Order` examples with giving the model
"a template for every new" instance. Keep them to a few lines and prefer a
`file:line` pointer when the real code is nearby **[HL] [BC]**.

### 6.7 Tone is a decision process, not a setting

"Professional tone. No slang." is an output state; "match where the reader
is, not where a brand guide says to be" is a decision process, and only the
second generalises to situations you never wrote a rule for **[TAI]**. The
same applies to "response length: concise" — it cannot tell the model whether
to shorten an explanation of a security bug.

---

## 7. Progressive disclosure — the map, not the territory

**Merged view.** Give the agent a map and let it fetch detail when relevant
**[HL] [BC] [BTN] [Docs]**:

```
agent_docs/
  building_the_project.md
  running_tests.md
  code_conventions.md
  service_architecture.md
  database_schema.md
  service_communication_patterns.md
```

In `CLAUDE.md`, one line per document saying what it holds and *when* to read
it, and an instruction to "evaluate relevance before reading" **[HL] [BC]**.
Prefer pointers to copies, `file:line` over pasted code **[HL] [BC]**.

### The mechanisms, and which actually defers cost

| Mechanism | Loads | Use for | Sources |
|---|---|---|---|
| A plain path mentioned in text ("see `docs/testing.md` when touching tests") | only if Claude reads it | true progressive disclosure | [HL] [Docs] |
| `@path` import | **at launch**, always | organising one logical file across several; sharing `AGENTS.md`; personal prefs from `~/` | [BC] [BTN] [Docs] |
| `.claude/rules/*.md` with `paths:` | when a matching file is read | per-directory or per-language conventions | [BC] [BTN] [Docs] |
| `.claude/rules/*.md` without `paths:` | at launch | splitting the root by topic for maintainability (no context saving) | [Docs] |
| `subdir/CLAUDE.md` | when files in the subtree are read | per-package rules in a monorepo | [BC] [CCBP] [Docs] |
| Skill (`SKILL.md` with `description`) | when invoked or judged relevant | multi-step procedures: scaffold an endpoint, triage tests, write a changelog | [Docs] [CCBP] [HL] |
| Slash command (`.claude/commands/`) | when invoked | repeatable task instructions such as a PR review checklist | [BC] [HL] |
| `CLAUDE.local.md` | at launch | personal preferences — ports, verbosity, IDE — kept out of the team file | [BC] [Docs] |
| Auto memory `MEMORY.md` | at launch (200 lines / 25 KB) | what Claude discovers and you confirm | [BC] [BTN] [Docs] |

**Difference described — imports.** **[BC]**'s progressive-disclosure example
uses `@agent_docs/building_the_project.md` for each document. Because imports
expand at launch **[Docs] [BTN]**, that pattern loads every document every
session and defers nothing; it is the opposite of progressive disclosure.
**[HL]**'s version — describe each file and tell Claude to read it when
relevant — is the one that saves context. Use `@` for what must always be
present (the shared `AGENTS.md`, a short personal-preferences file) and plain
pointers for everything else.

**Difference described — conditional sections.** **[CCBP]**'s
custom-instructions guide puts `## When writing tests`, `## When refactoring`,
`## When reviewing PRs` and named personas ("Strict Reviewer", "Security
Auditor") in the root file and says "Claude applies the relevant section based
on what you ask". **[HL]** wants only universally applicable instructions in
the root, because non-universal ones are exactly what the harness's relevance
reminder tells the model to ignore, and they spend budget every session.
**[Docs]** agrees with **[HL]**: "if an entry is a multi-step procedure or only
matters for one part of the codebase, move it to a skill or a path-scoped
rule". The persona pattern is legitimate as a skill or a subdirectory file,
not as always-loaded root content.

**Twelve-Factor's version of the same idea.** Factor 10 — small, focused
agents with a clear scope — maps onto small, focused instruction files with a
clear scope; Factor 3's information density ("same message, fewer tokens";
XML-style blocks; hide errors once resolved) maps onto dense root files and
detail behind pointers; Factor 13 — "if you already know what tools you'll
want the model to call, just call them deterministically and let the model do
the hard part of figuring out how to use their outputs" — is the argument for
putting the test command and the entry-point path *in* the file rather than
making the agent discover them every session **[12FA]**.

---

## 8. Enforcement — what the file cannot do, and what does it instead

**Merged view.** "For behavior that can never break, use hooks instead of
longer files. Hooks provide deterministic enforcement, while CLAUDE.md remains
advisory guidance" **[BTN] [HL] [BC] [Docs] [CCBP]**. The official split
**[Docs]**:

| Concern | Configure in |
|---|---|
| Block specific tools, commands or file paths | `permissions.deny` |
| Something that must run at a fixed point (before every commit, after every edit) | a hook |
| Sandbox isolation, environment, login restrictions | managed settings |
| Code style and quality guidance, data-handling reminders, behavioural instructions | `CLAUDE.md` |

"Settings rules are enforced by the client regardless of what Claude decides
to do. CLAUDE.md instructions shape Claude's behavior but are not a hard
enforcement layer" **[Docs]**.

### 8.1 Hooks — the contract and the recipes

* Hooks live in `settings.json` (`~/.claude/` or `.claude/`) under
  `hooks.<Event>[].hooks[]` with `{"type": "command", "command": …}`; the
  script receives the event as **JSON on stdin** (`tool_input.file_path`,
  `tool_input.command`, …) **[CCBP]** dogfood, starters and `tools/hooks/`;
  **[Docs]**. Exit `0` = allow, `2` = block with **stderr** shown to Claude;
  anything else is treated as a script bug **[CCBP]**.
* Recipes that recur across sources: a `PreToolUse` guard on `Write|Edit`
  that refuses secrets and sensitive filenames (`block-secrets.sh`); a
  `PostToolUse` formatter on `Write|Edit` that stays silent if no formatter is
  installed (`format-on-write.sh`); a `Stop` hook that runs the test suite and
  reports the tail of failures into the next turn (`test-on-stop.sh`)
  **[CCBP]**; a `Stop` hook running an auto-fixing linter such as Biome so
  style never enters the prompt **[HL]**; a `PreToolUse` hook that lints any
  `CLAUDE.md` before it is written (the `claude-md-checker` plugin) **[CCBP]**.
* Hook anti-patterns **[CCBP]** AP-7…AP-10: a hook that calls Claude
  (recursive cost, loops); a hook that swallows its own failure with
  `2>/dev/null` and no `set -euo pipefail` ("six months later half the repo
  was never formatted"); exit `1` where the contract says `2`; matching all of
  `Bash` for a rule meant for `git commit` — match narrowly and short-circuit
  inside the script.

**Difference described — the hook interface.** **[BC]** refers to
`.claude/hooks.json`; **[CCBP]**'s hooks *guide* documents environment
variables (`$CLAUDE_FILE_PATH`, `$CLAUDE_COMMAND`), a flat `command` key and a
`PreUserPromptSubmit` event, and `examples/hook-scripts.md` uses a `"hook"`
key and exit `1`. The same repo's shipped and dogfooded configuration — and
the official docs — use `settings.json`, the nested `type: command` form,
stdin JSON, and exit `2`. Trust the shipped scripts and the documentation,
not the prose.

### 8.2 Permissions

* Prefer an **allowlist** of the hot path (test runner, linter, formatter,
  dev server, read-only git) to a denylist; add entries as Claude asks for
  them in practice; be explicit (`Bash(npm test)`), not `Bash(npm run *)`
  **[CCBP]**. Even under auto mode, "write allow rules for your hot path
  anyway — explicit rules are cheaper to evaluate and fully predictable"
  **[CCBP]**.
* **Deny** `git push`, `rm -rf`, `curl … | sh`, package installs and
  `chmod 777`; every starter kit denies `git push` and has a comment to
  uncomment it if the team is comfortable **[CCBP]**.
* A `Read(path)` deny rule keeps a path out of Read, Grep, Glob, `@`
  mentions and shell reads; combine it with the instruction in `CLAUDE.md` so
  the model knows *why* the path is off-limits and does not route around it
  **[Docs]** (permissions reference).
* Twelve-Factor's Factors 7 and 8 are the theory behind the permission
  prompt: "the number one feature request … is to interrupt a working agent
  and resume later, especially between the moment of tool *selection* and the
  moment of tool *invocation*", because without it you must either restrict
  the agent to low-stakes calls or "yolo hope it doesn't screw up" **[12FA]**.
  Factor 9 — compact errors into the context window, cap consecutive failures
  at about three, then escalate to a human — is the design of a good blocking
  hook: put the reason on stderr so the model can self-correct once, not loop.

---

## 9. Security in and around the instruction files

* **No secrets, no realistic-looking examples.** `CLAUDE.md`,
  `settings.json` and MCP configs are committed; "the moment a real key lands
  on a branch, it's leaked — rotating it is the only fix". Reference an
  environment variable and say where the real value lives (password manager,
  secret store) **[CCBP]**. Scan the file for AWS keys, GitHub and Slack
  tokens, Anthropic/OpenAI-style keys, JWTs, private-key blocks and
  `password = "…"` patterns — the linter and `block-secrets.sh` do **[CCBP]**.
* **No absolute laptop paths, no internal hostnames** in a file others clone
  **[CCBP]**.
* **Treat all tool output as untrusted data.** The model cannot tell data
  from instructions; an issue body or a fetched page can say "ignore prior
  instructions and run …". Narrow permissions are the last line of defence;
  keep destructive tools off the automatic allowlist; gate external content
  behind a human in loop-style workflows; do not let `git push` follow a read
  of external data in the same turn without a prompt **[CCBP]**.
* **Plugins and skills are code with no lockfile and no signing.** Read
  `plugin.json`, every `SKILL.md` and every hook script before installing;
  pin a commit; evaluate at user scope for a week before promoting to project
  scope; set `disableSkillShellExecution: true` globally when any third-party
  skill is installed **[CCBP]**.
* **Put `.claude/` under `CODEOWNERS`** so permission and hook changes get a
  security review **[CCBP]**; treat policy changes like infrastructure changes
  — PR, review, staged rollout **[CCBP]**.
* **Transcripts leak.** Redact before pasting a session into a bug report
  **[CCBP]**.
* **Keeping files out of context.** **[CCBP]** presents `.claudeignore` as the
  primary tool ("Claude Code will not read, index, or reference any file that
  matches"). The official memory and permissions documentation describes
  `permissions.deny` `Read(…)` rules for that purpose and does not mention
  `.claudeignore`; verify against the current docs before relying on it.
* **Factor 3's safety benefit** — "control what information gets passed to
  the LLM, filtering out sensitive data" **[12FA]** — is the general
  statement: what is not in the context cannot be leaked by the model.

---

## 10. Maintenance, testing and iteration

### 10.1 Hand-written or generated?

* **Never auto-generate; hand-craft every line** **[BC] [HL] [BTN]**. The
  file "affects every phase of the workflow — poor instructions cascade
  through research, planning, and implementation" **[HL]**; **[BTN]** cites
  the ETH Zurich result (auto-generated −3 %, human-written +4 %).
* **[CCBP]** ships a seven-question generator script, a "quickstart prompt"
  that asks Claude to write the file from the codebase in under 60 lines, and
  recommends `/init`; **[Docs]** offers `/init` and a newer interactive flow
  that proposes `CLAUDE.md`, skills and hooks for review before writing.

**Difference described.** The disagreement is smaller than it looks. All
sources agree the final file must be reviewed and owned by a human; the
generation critics object to *committing the generator's output as-is*, and
the generation advocates all say "review the output, remove anything
inaccurate, add team rules Claude could not infer" **[CCBP]** and "refine from
there with instructions Claude wouldn't discover on its own" **[Docs]**. A
generated file is a reasonable *inventory* of commands and layout; the
constraints, tradeoffs and audience (§4.2–4.4) — the parts that carry the
value — can only be written by someone who knows why the project is the way
it is.

### 10.2 Grow it from real mistakes, prune it on a schedule

* Add on the second occurrence, not the first (§4.5) **[Docs] [BC] [CCBP]**.
* "Update regularly … stale instructions cause confusion" **[CCBP]**; review
  all `CLAUDE.md`, nested files and rules "periodically to remove outdated or
  conflicting instructions" — contradictions are resolved arbitrarily
  **[Docs]**; add the review to sprint retros or quarterly reviews **[CCBP]**;
  run `/doctor` for trim proposals **[Docs]**.
* Keep the file **stable** during a benchmark or a long working period: it is
  part of the cached prompt prefix, and churn breaks cache hits **[CCBP]**.
* "Edit existing files over creating new ones … a file that isn't linked is
  invisible" **[CCBP]** dogfood — applies to `agent_docs/` as much as to
  guides.

### 10.3 Test that it loaded and that it is followed

* `/context` → **Memory files** is the only proof the file loaded; if it is
  not listed, Claude cannot see it **[Docs]**.
* Ask Claude, before it starts, "tell me what rules you're following for this
  task"; compare output consistency across sessions; when it deviates, add the
  correction as an explicit rule rather than repeating it in chat **[CCBP]**.
* `InstructionsLoaded` hook to log which instruction files loaded and why
  **[Docs]**.
* Lint the file: **[CCBP]**'s `lint-claude-md.sh` errors on a missing H1, a
  missing Commands section and hard-coded secrets; warns on no Architecture,
  no testing information, no guardrails section, under 10 or over 200 lines,
  commands not in backticks, vague phrases, absolute paths, retired model IDs
  and empty sections. `audit-claude-setup.sh` scores a project out of 100:
  `CLAUDE.md` present with 3+ sections and reasonable length (35), valid
  `settings.json` without secrets (25), a non-empty allowlist with `git push`
  denied (25), hooks configured with scripts on disk (15) — "treat the score
  as a floor, not a target".
* Measure: **[CCBP]**'s harness runs the same task set with and without the
  file; if you run only two comparisons in your own repo, run Sonnet-vs-Opus
  on your common task shapes and plan-mode on/off on your next refactor.
* Twelve-Factor's Factor 2 lists what owning the prompt buys: "build tests
  and evals for your prompts just like you would for any other code", iterate
  on real-world performance, and know exactly what the agent is working with
  **[12FA]**. Twelve-Factor's own workshop `CLAUDE.md` is an example of the
  iteration loop working: a "Key Implementation Learnings" section of
  one-line facts discovered the hard way ("No async/await in notebooks",
  "BAML test support works, contrary to initial assumption").

### 10.4 Team and organisation scale

* Commit the project file and `.claude/settings.json`; keep personal
  preferences in `~/.claude/CLAUDE.md` or `CLAUDE.local.md`; settings
  precedence is enterprise > project > user **[CCBP] [Docs]**.
* Monorepo: root 40–80 lines of cross-cutting rules, 20–40 per package
  **[CCBP]**; template repositories so new repos start configured **[CCBP]**;
  a CI check that `.claude/settings.json` still has its deny list and
  `CLAUDE.md` exists **[CCBP]**; `claudeMdExcludes` for other teams' files
  **[Docs]**.
* A managed `CLAUDE.md` (or the `claudeMd` settings key) for organisation-wide
  behavioural guidance; managed settings for anything that must be enforced
  **[Docs]**.

---

## 11. Anti-pattern gallery, consolidated

| # | Anti-pattern | Fix | Sources |
|---|---|---|---|
| 1 | Vague instructions ("write clean code", "be careful") | one concrete action per line, with its why | [CCBP] AP-1, [Docs], [BC] |
| 2 | Empty or outline-only sections | delete until there is content | [CCBP] AP-2 |
| 3 | Pinned model IDs | describe the selection criterion | [CCBP] AP-3 |
| 4 | Absolute paths from one machine | repo-relative paths | [CCBP] AP-4 |
| 5 | Secrets in the file | env var + where the real value lives | [CCBP] AP-5, all |
| 6 | One 600-line monolith for a monorepo | per-package files, root for cross-cutting rules | [CCBP] AP-6 |
| 7 | Style rules the linter could enforce | formatter in a hook | [HL] [BC] [BTN] |
| 8 | Task-specific or one-off instructions in the root | skill, slash command, `paths:` rule | [HL] [BC] [Docs] |
| 9 | Hotfix added after a single misbehaviour | wait for the second; or a hook | [BC] [HL] [Docs] |
| 10 | Restating what `package.json` or the tree already says | delete; `/doctor` | [BTN] [CCBP] [Docs] |
| 11 | Pasted code snippets | `file:line` pointers | [HL] [BC] |
| 12 | `@`-importing every reference doc "for progressive disclosure" | plain pointers; import only what must always load | [Docs] [BTN] vs [BC] |
| 13 | Every line in bold, caps, "MANDATORY", "CRITICAL" | emphasise the one or two lines that must never be missed | [12FA] root file as counter-example; [BC] [BTN] periphery finding |
| 14 | Bare rule list with no values, intent or tradeoffs | add the why and the tradeoff statement; name the audience | [TAI] |
| 15 | Tone or length as an output state ("concise", "professional") | describe the decision process | [TAI] |
| 16 | Two rules that contradict across files | review and remove; the model picks arbitrarily | [Docs] |
| 17 | Committing generator or `/init` output unreviewed | review, cut, add what only you know | [BC] [HL] [BTN] [CCBP] [Docs] |
| 18 | Believing the file is enforced | hooks and permissions for anything that must hold | [BTN] [HL] [Docs] [CCBP] |
| 19 | Hook that calls Claude, swallows errors, exits 1, or matches all of `Bash` | deterministic, `set -euo pipefail`, exit 2 + stderr, narrow matcher | [CCBP] AP-7…10 |
| 20 | Never checking `/context` | confirm the file is under **Memory files** | [Docs] |

---

## 12. A merged skeleton

What survives when every source's must-haves are combined and every
exclusion applied. Aim at 60–100 lines filled in; each `##` is optional if
empty.

```markdown
# <project name> — <one line: what it is and who it serves>

<2–4 sentences: purpose, the audience the output is for, and the one or two
tradeoffs that decide edge cases — e.g. "clarity over brevity when a decision
is not obvious from the code".>

## Structure                      <!-- only what is not derivable -->
- `apps/api/` — the one to change for backend work; `apps/web/` calls it
- `packages/shared/` — types imported by both; breaking changes here break everything

## Commands                       <!-- exact, in backticks, incl. single test -->
- `pnpm test` / `pnpm test -- --grep "<name>"`
- `pnpm lint && pnpm typecheck` — run before committing; CI blocks on both

## Conventions that differ from the defaults   <!-- rule + one-clause why -->
- Named exports only — large refactors are cleaner
- Never edit `internal/store/` — generated by sqlc, overwritten on build

## Do NOT
- Add dependencies without asking — the lockfile is reviewed
- Trust a client-supplied user id — derive it from the session

## Where the detail lives         <!-- pointers, read when relevant -->
- `docs/testing.md` — before touching tests
- `docs/architecture.md` — before changing service boundaries
- Personal preferences: `CLAUDE.local.md` (gitignored)
```

With, beside it: `.claude/settings.json` (allowlist of the hot path; deny
`git push`, `rm -rf`; `block-secrets` on `PreToolUse Write|Edit`; formatter on
`PostToolUse`; tests on `Stop`), `.claude/rules/` for `paths:`-scoped
conventions, and skills for procedures.

---

## 13. Index of disagreements

| Topic | Positions | Resolution used above |
|---|---|---|
| Line ceiling | 60 [BTN][HL root][BC teams] · 100 [BC ideal] · 200 [Docs][BTN][CCBP] · 300 [HL][BC][BTN max] | root ≲100, launch total ≲200, never 300; count instructions not lines |
| Import depth | 4 [Docs] · 5 [BC] | 4 |
| Imports as progressive disclosure | yes [BC] · no, they load at launch [Docs][BTN][HL by construction] | plain pointers; `@` only for always-needed files |
| Bullets vs prose | bullets [Docs][CCBP] · prose for values [TAI] | bullets for look-ups, prose for tradeoffs |
| Explain the why | yes [TAI][HL][BC][CCBP AP-1][Docs consistency] · budget pressure [HL][BC][BTN] | one-clause reason, only where there is an edge case |
| Code style in the file | never [HL][BC][BTN] · templates full of it [CCBP] | only conventions no linter enforces |
| Architecture / WHAT section | include [BC][HL][CCBP] · derivable, trim [BTN][Docs /doctor] | keep what a tree cannot tell you (which app, why) |
| Auto-generation | never [BC][HL][BTN] · tools and `/init` [CCBP][Docs] | generate an inventory, hand-write the constraints, review all of it |
| Precedence | later files override [CCBP] · concatenated, no override [Docs] | concatenated |
| Compaction | may push the file out [CCBP] · root is re-read from disk [Docs] | re-read |
| Position of key rules | top [CCBP] · top and bottom [BC][BTN] | top and bottom; one emphasised line |
| Conditional / persona sections in the root | yes [CCBP] · universal only [HL]; move to skills/rules [Docs] | skills and subdirectory files |
| Do-NOT section vs positive phrasing | both within [CCBP] | prohibitions when the positive form has no home |
| Hook interface | `.claude/hooks.json` [BC] · env vars, flat key, exit 1 [CCBP guide/examples] · `settings.json`, stdin JSON, exit 2 [Docs][CCBP scripts] | the shipped scripts and the docs |
| Keeping files out of context | `.claudeignore` [CCBP] · `permissions.deny Read()` [Docs] | verify `.claudeignore` against current docs before relying on it |
| Instruction budget 150–200 | asserted, unsourced [HL][BC][BTN] | order of magnitude; the uniform-degradation claim is the usable part |
| Compliance decay 95 % → 20–60 % | asserted, unsourced [BTN] | direction plausible; do not quote as measured |

---

## 14. Reading order for someone new

1. **[HL]** for the mental model (stateless function, budget, progressive
   disclosure, linter's job) — ten minutes.
2. **[Docs]** for the mechanics that decide what actually loads — the load
   table, imports, rules, `/context`.
3. **[TAI]** for the part everyone else skips — values, tradeoffs, audience.
4. **[CCBP]** `examples/claude-md-minimal.md`, then one template for your
   stack, then `guides/anti-patterns.md`; run `tools/lint-claude-md.sh` and
   `tools/audit-claude-setup.sh` on your repo.
5. **[BC]** and **[BTN]** as compact checklists to re-read when the file has
   grown.
6. **[12FA]** Factors 2, 3, 8, 10 and 13 when you start wiring hooks,
   permissions and skills around the file — they are the design principles
   those mechanisms implement.

*Applied in this vault:* `base/VAULT.md` and each repo's `AGENTS.md` follow
this document — root under 100 lines, one emphasised line per file, commands
and gates as sections, the private-tree rule enforced by `permissions.deny`
rather than by instruction alone, detail behind pointers into `RULES.md`,
`WORKING-RULES.md` and `docs/`. Change those files with this document open.
