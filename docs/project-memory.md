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

## Validating

```bash
agents-memory-check [repo]        # default: the enclosing Git repository
```

Checks that `.agents/memory/` is ignored by Git, then validates every memory
against the contract above: filename form, 100-line and 32 KiB ceilings, a
level-one title on the first content line, no symlinks or nested directories,
and no private-key markers or secret-looking assignments. Every violation is
reported, and the exit status is non-zero if there was any, so it works as a
pre-commit or CI gate. An absent `.agents/memory/` is not an error — memory is
opt-in.

The generated `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md` tell both agents to
read memory relevant to the task. Writing one is a procedure rather than a
standing rule, so it lives in the `project-memory` skill, which carries this
command and the routing decision for what belongs in memory at all.

**Removed:** `dotfiles memory init`, `list`, and `migrate`. Creating the
directory is `mkdir -p .agents/memory` (the ignore rule is already global, in
`home/dot_gitignore`), listing it is `ls`, and the migration from the obsolete
`.claude/memory/`, `.codex/memories/`, and `.agents/memories/` layouts is
finished. See git history if you need the old implementations.

## Native memory systems

Claude's auto memory is tool-private and repository-scoped outside the project.
Codex's native local memory is tool-private under the Codex home directory.
They may coexist, but this dotfiles setup does not depend on either system for
shared project knowledge.
