# Shared agent skills

The dotfiles manager uses the portable Agent Skills directory format supported
by Claude Code and Codex:

```text
<skill-name>/
├── SKILL.md
├── agents/openai.yaml     # optional Codex UI metadata; ignored by Claude Code
├── references/            # optional, loaded only when needed
└── scripts/               # optional deterministic helpers
```

First-party skills are stored under
`src/dotfiles/resources/agents/skills/`. A normal `dotfiles install`
copies them to both personal discovery locations:

- Claude Code: `~/.claude/skills/`
- Codex: `~/.agents/skills/`

## Optional GPTomics skills

```bash
dotfiles skills install [--with GROUP]... [--dry-run]
dotfiles skills update [--with GROUP]... [--dry-run]
dotfiles skills status
```

Both install and update include the default RNA-seq and single-cell group. Add
`--with spatial` or `--with genomics` as needed. Downloaded source is cached in
`~/.local/share/dotfiles/bioskills`; installed copies use the same directory
layout for both agents and receive namespaced metadata names.

The `all` group contains 561 skills and can crowd each agent's discovery
catalog. It therefore requires an explicit acknowledgement:

```bash
dotfiles skills install --with all --allow-large
```

`--dry-run` reports intended work without copying or downloading anything.
`skills status` validates installed metadata and reports both agent locations.

## Authoring rules

- Put cross-agent skills under `resources/agents/skills/`.
- Use only portable `name` and `description` frontmatter in `SKILL.md`.
- Put Codex-only UI metadata under `agents/openai.yaml`.
- Avoid Claude-specific substitutions in shared instructions. Refer to the
  directory containing `SKILL.md` as `<skill-dir>` when invoking bundled files.
- Keep detailed knowledge in direct `references/` links and deterministic work
  in `scripts/`.
- Validate every bundled skill before release.
