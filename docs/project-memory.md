# Shared project memory

Claude Code and Codex share durable repository-specific discoveries through
`.agents/memory/`. This is a dotfiles convention: neither agent discovers the
directory natively. Their generated global `CLAUDE.md` and `AGENTS.md` files
tell them to scan memory filenames and read only files relevant to the task.

## Contract

Each memory is a direct Markdown file with a lowercase, hyphenated name:

```text
.agents/memory/
├── integration-tests-require-redis.md
└── dataset-identifiers-use-ensembl.md
```

A valid memory:

- starts with one level-one title;
- records one durable, non-obvious project fact or closely related decision;
- stays at or below 100 lines and 32 KiB;
- contains no secrets, transcripts, temporary task state, or facts already
  clear from project files; and
- is updated or removed when evidence changes.

Required rules belong in checked-in `AGENTS.md`, `CLAUDE.md`, or project
documentation. Memories are advisory and material claims should be checked
against the current repository before use.

Reading memories is covered by the generated global instructions. Writing them
is covered by the `project-memory` skill, which holds the routing decision
(memory, project instructions, or nothing) and the authoring rules.

## Commands

```bash
dotfiles memory init [--repo DIR]
dotfiles memory list [--repo DIR] [--json]
dotfiles memory check [--repo DIR] [--json]
dotfiles memory migrate [--repo DIR] [--apply]
```

`init` safely creates the directory. `list` prints filenames, titles, and line
counts without displaying memory bodies. `check` validates names, size, title,
file type, basic secret patterns, and Git ignore behavior.

`migrate` inspects `.claude/memory/`, `.codex/memories/`, and
`.agents/memories/`. Its default mode is a plan. `--apply` copies only files
that already satisfy the current contract. It never deletes legacy files,
copies symlinks, or automatically converts session summaries; those require
manual review and splitting into topic memories.

## Native memory systems

Claude's auto memory is tool-private and repository-scoped outside the project.
Codex's native local memory is tool-private under the Codex home directory.
They may coexist, but this dotfiles setup does not depend on either system for
shared project knowledge.
