# Agent context architecture

## Principle: progressive disclosure

Agent context is limited. Load only what is relevant to the current task and
retrieve specialized knowledge when needed instead of pre-loading everything.

## Shared instruction hierarchy

```text
canonical:
    home/.chezmoitemplates/
        agents-preferences.md          shared cross-agent preferences
        claude-instructions.md         Claude-specific supplement
        codex-instructions.md          Codex-specific supplement
        codeocean-preferences.md       appended for the Code Ocean profile
        codex-preferences.toml         Codex config fragment

sources:
    home/dot_claude/CLAUDE.md.tmpl     composes shared + Claude + environment
    home/dot_codex/AGENTS.md.tmpl      composes shared + Codex + environment
    home/dot_claude/skills/            shared cross-agent workflows

installed:
    ~/.claude/CLAUDE.md                shared + Claude + environment
    ~/.codex/AGENTS.md                 shared + Codex + environment
    ~/.agents/skills -> ~/.claude/skills

project-specific:
    <repo>/CLAUDE.md or AGENTS.md      stable project conventions

scoped/procedural:
    shared Agent Skills                retrieved when applicable

learned/temporary:
    .agents/memory/*.md, plans,
    scratch context                    project-local or discardable state
```

chezmoi generates the two global instruction files from the canonical shared
preferences and their small tool-specific supplements. This keeps
Claude and Codex aligned without putting Claude model names in Codex guidance.

### What belongs where

| Layer | Contains |
|---|---|
| Shared preferences | Universal working style, engineering, notebooks, memory, and safety rules |
| Tool supplement | Delegation and model/effort guidance specific to Claude or Codex |
| Profile overlay | Environment invariants such as filesystem layout and resource limits |
| Project instructions | Stable conventions every session in that repository needs |
| Agent skills | Scoped or procedural knowledge fetched when applicable |
| Project memory | Local `.agents/memory/*.md` files shared by both agents |
| Temporary context | Plans, debug notes, and task state that can be discarded |

## Configuration parity

Behavioral preferences live in the generated Markdown instructions. Enforceable
secret-read protections live in tool configuration:

- Claude uses the deny list in `~/.claude/settings.json`.
- Codex uses a `dotfiles` permission profile merged into
  `~/.codex/config.toml`.

Codex's configuration file also contains app-owned state such as plugins,
notification commands, and trusted projects. The installer owns only a marked
preference block and preserves the rest of the file byte-for-byte. It refuses
invalid TOML, symlink destinations, malformed markers, and unmanaged key
collisions.

Settings without true equivalents are intentionally not translated. Claude's
30-day cleanup, `.gitignore`, remote-control, and plan-mode switches remain
Claude settings; Codex keeps its native behavior. Plugin, MCP, and skill parity
is managed separately from preferences.

## Project memory policy

Claude and Codex share one repository-local memory directory:
`.agents/memory/`. Each durable memory is an individual Markdown file with a
concise, descriptive filename. Agents scan filenames at the start of repository
work and read only files relevant to the current task.

The directory is globally Git-ignored. Do not include transcripts, temporary
task status, secrets, sensitive data, or facts already evident from project
files. Update or remove stale and conflicting files rather than accumulating
duplicates.

See [Shared project memory](project-memory.md) for the file contract and the
`agents-memory-check` validator.

**Bad:**

> Yesterday we spent a long time debugging Redis and eventually discovered
> that integration tests failed because REDIS_URL wasn't set.

**Good:**

> Integration tests require REDIS_URL.

Promote a fact only when it is useful in a future session. Stable project
invariants belong in project instructions or documentation. Non-obvious learned
facts may go in `.agents/memory/`. Everything else should be discarded.

Do not automatically promote every correction into permanent global guidance.
Global preferences should change only for genuinely cross-project behavior.

## Measuring context size

Budgets are enforced by the test suite, not at runtime — these files are
generated from the source tree, so their size is a repository invariant:

```bash
pytest -k budget
```

| Layer | Estimated-token limit |
|---|---:|
| Generated global instructions | 900 |
| Environment overlay | 500 |

The deterministic estimate is `words × 4/3` and requires no tokenizer or
external service. The budgets and the estimator live in
`tests/test_claude_context.py`; a failing assertion prints the measured count.
To inspect an installed file directly, `wc -w ~/.claude/CLAUDE.md`.

## Memory maintenance

Periodically remove stale or duplicate memory files and resolve contradictions.
Promote required project invariants into project documentation or instructions.
