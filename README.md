# kb-base

The shared machinery of a plain-Markdown, git-native personal knowledge base:
a linter, a note creator, note templates, a controlled tag vocabulary, and the
rules for what a note must contain and where it goes.

**`RULES.md` is the document to read.** It is written for anyone building a
knowledge base of their own: one note answers one question and states its
answer first; four repos separated by *who is harmed if it leaks*, not by topic;
tags as facets, never keywords; secrets referenced by location, never by value.

## Use it with a content repo

```
mkdir kb && cd kb
git clone https://github.com/aiaibox/kb-base   base
git clone https://github.com/aiaibox/kb-public public     # or your own
git -C public config core.hooksPath ../base/.githooks
cd public && python3 scripts/lint.py
```

Everything is Python 3.9+ standard library and POSIX shell. No dependencies.
