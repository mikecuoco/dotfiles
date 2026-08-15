---
name: project-memory
description: Write, update, and prune durable project memories under .agents/memory/, and decide whether a fact belongs in memory, in checked-in project instructions, or nowhere. Use when recording a non-obvious project discovery or decision, when asked to remember something about a repository, when reviewing stale or conflicting memories, or when proposing a change to a project's CLAUDE.md or AGENTS.md.
---

# Project Memory

Project memories are individual Markdown files under `<repo>/.agents/memory/`.
They are a dotfiles convention rather than a native agent feature, and they are
local to the checkout: they are not committed and do not reach collaborators or
other machines. Anything a teammate must follow belongs in checked-in project
instructions instead.

Reading memories is covered by the global preferences. This skill covers
deciding what to record and writing it.

## Route the fact first

Not every discovery belongs in memory. Before writing anything, place it:

| The fact is… | It belongs in… |
|---|---|
| A durable, non-obvious property of this repository | `.agents/memory/` |
| A rule contributors must follow | Checked-in `CLAUDE.md` / `AGENTS.md` |
| Already visible in the code, config, or git history | Nowhere — do not record it |
| Task status, a transcript, or a session summary | Nowhere — it expires |
| A secret, credential, or sensitive path | Nowhere, ever |

Prefer project instructions over memory for anything stable and required.
Propose those updates only for verified, non-obvious conventions, and exclude
transient notes and secrets.

## Write the memory

Follow the contract in `docs/project-memory.md`, which is canonical — do not
restate its limits here. In short: one lowercase, hyphenated file per fact, one
level-one title, and one durable fact or closely related decision per file.

- Name the file after the fact, not the task: `integration-tests-require-redis.md`,
  not `testing-notes.md`.
- State the fact and the evidence for it. A memory that cannot be checked
  against the repository cannot be trusted later.
- Keep it short. If a file needs sections for unrelated facts, split it.

## Update instead of duplicating

Before creating a file, scan existing filenames for the same subject.

- Superseded by new evidence → update the file in place.
- Contradicted by the current repository → correct or remove it; do not leave
  both versions.
- No longer true → remove it. A wrong memory is worse than a missing one.

## Validate and report

After any change:

```bash
dotfiles memory check --repo <repo>
```

This validates names, size, title, file type, basic secret patterns, and Git
ignore behavior. Mention every file created, updated, or removed in the final
response — memory changes are invisible to the user otherwise.
