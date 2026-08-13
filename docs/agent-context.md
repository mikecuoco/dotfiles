# Agent context architecture

## Principle: progressive disclosure

Agent context is limited. Load only what is relevant to the current task and
retrieve specialized knowledge when needed instead of pre-loading everything.

## Shared instruction hierarchy

```text
canonical:
    common/agents/PREFERENCES.md       shared cross-agent preferences

tool-specific:
    common/claude/CLAUDE.md            Claude delegation policy
    common/codex/AGENTS.md             Codex delegation policy

environment-specific:
    codeocean/agents/PREFERENCES.md    appended for the Code Ocean profile

installed:
    ~/.claude/CLAUDE.md                shared + Claude + environment
    ~/.codex/AGENTS.md                 shared + Codex + environment

project-specific:
    <repo>/CLAUDE.md or AGENTS.md      stable project conventions

scoped/procedural:
    rules and skills                   retrieved when applicable

learned/temporary:
    memories, plans, scratch context   conclusions persist; transcripts do not
```

The installer generates the two global instruction files from the canonical
shared preferences and their small tool-specific supplements. This keeps
Claude and Codex aligned without putting Claude model names in Codex guidance.

### What belongs where

| Layer | Contains |
|---|---|
| Shared preferences | Universal working style, engineering, notebooks, memory, and safety rules |
| Tool supplement | Delegation and model/effort guidance specific to Claude or Codex |
| Profile overlay | Environment invariants such as filesystem layout and resource limits |
| Project instructions | Stable conventions every session in that repository needs |
| Rules and skills | Scoped or procedural knowledge fetched when applicable |
| Memory | Durable, non-obvious conclusions rather than task transcripts |
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

## Memory policy

Store conclusions, not transcripts.

**Bad:**

> Yesterday we spent a long time debugging Redis and eventually discovered
> that integration tests failed because REDIS_URL wasn't set.

**Good:**

> Integration tests require REDIS_URL.

Promote a fact only when it is useful in a future session. Stable project
invariants belong in project instructions or documentation. Non-obvious learned
facts may go to memory. Everything else should be discarded.

Do not automatically promote every correction into permanent global guidance.
Global preferences should change only for genuinely cross-project behavior.

## Measuring context size

Use the compatibility-aware reporter:

```bash
dotfiles agent-stats
```

`dotfiles claude-stats` remains an alias. The report measures the effective
Claude and Codex global instructions plus any environment overlays.

Budgets are warnings rather than hard runtime limits:

| Layer | Estimated-token limit |
|---|---:|
| Generated global instructions | 800 |
| Environment overlay | 500 |

The deterministic estimate is `words × 4/3` and requires no tokenizer or
external service.

## Memory maintenance

A future memory-garbage-collection workflow could remove stale entries, merge
duplicates, shorten verbose facts, resolve contradictions, promote stable
project invariants into project documentation, and demote inappropriate global
instructions.

Until then, periodically prune each tool's memory store manually. External
memory systems such as Mem0 remain deferred until native memory has been
evaluated across multiple project types.
