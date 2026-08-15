# Agent context architecture

## Principle: progressive disclosure

Agent context is limited. Load only what is relevant to the current task and
retrieve specialized knowledge when needed instead of pre-loading everything.

## Shared instruction hierarchy

```text
canonical:
    common/agents/PREFERENCES.md       shared cross-agent preferences
    common/agents/skills/              shared cross-agent workflows
    common/agents/skills.toml          optional external skill groups

tool-specific:
    common/claude/CLAUDE.md            Claude delegation policy
    common/codex/AGENTS.md             Codex delegation policy

environment-specific:
    codeocean/agents/PREFERENCES.md    appended for the Code Ocean profile
    cluster/agents/PREFERENCES.md      appended for the HPC cluster profile

installed:
    ~/.claude/CLAUDE.md                shared + Claude + environment
    ~/.codex/AGENTS.md                 shared + Codex + environment

project-specific:
    <repo>/CLAUDE.md or AGENTS.md      stable project conventions

scoped/procedural:
    shared Agent Skills                retrieved when applicable

learned/temporary:
    .agents/memory/*.md, plans,
    scratch context                    project-local or discardable state
```

The installer generates the two global instruction files from the canonical
shared preferences and their small tool-specific supplements. This keeps
Claude and Codex aligned without putting Claude model names in Codex guidance.

### What belongs where

| Layer | Contains |
|---|---|
| Shared preferences | Safety, working style, and engineering rules, plus any prohibition that must already be loaded before the agent acts |
| Tool supplement | Delegation and model/effort guidance specific to Claude or Codex |
| Profile overlay | Environment invariants such as filesystem layout and resource limits |
| Project instructions | Stable conventions every session in that repository needs |
| Agent skills | Procedures, recipes, and checklists whose trigger can be named in a `description` and fetched when applicable |
| Project memory | Local `.agents/memory/*.md` files shared by both agents |
| Temporary context | Plans, debug notes, and task state that can be discarded |

### Preference or skill

Preferences cost context on every turn of every session. Skills cost nothing
until they trigger, but a skill that never triggers is worse than the
preference line it replaced. Two checks decide it:

1. Can you write a `description` that reliably matches the moment the rule
   matters? If not, it cannot be a skill.
2. If the agent never loads it, what breaks? Irreversible damage means it stays
   a preference regardless of length.

In practice, prohibitions belong in preferences and procedures belong in
skills. A rule split across both — such as project memory, where reading is a
preference and authoring is a skill — should be split at that boundary rather
than duplicated.

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

See [Shared project memory](project-memory.md) for the file contract, CLI
validation, and conservative legacy migration behavior.

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

Use the compatibility-aware reporter:

```bash
dotfiles agent-stats
```

`dotfiles claude-stats` remains an alias. The report measures the effective
Claude and Codex global instructions plus any environment overlays.

Budgets are warnings rather than hard runtime limits:

| Layer | Estimated-token limit |
|---|---:|
| Generated global instructions | 900 |
| Environment overlay | 500 |

The deterministic estimate is `words × 4/3` and requires no tokenizer or
external service.

## Memory maintenance

Periodically remove stale or duplicate memory files and resolve contradictions.
Promote required project invariants into project documentation or instructions.
