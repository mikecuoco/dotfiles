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

First-party skills live in the chezmoi source at `home/dot_claude/skills/` and
install like any other managed file — `chezmoi apply` (or `dotfiles install`)
puts them in `~/.claude/skills/`.

`~/.agents/skills` is a managed symlink to that directory, so Codex reads the
same tree. The two used to be independent copies kept in step by the installer;
linking them removes the possibility of drift and means anything writing skills
has one destination rather than two.

## GPTomics bioSkills

```bash
dotfiles skills install [--dry-run]
dotfiles skills update [--dry-run]
dotfiles skills status
```

These are fetched from [GPTomics/bioSkills](https://github.com/GPTomics/bioSkills)
and cached in `~/.local/share/dotfiles/bioskills`. `install` clones on first run
and reuses the cache afterwards; `update` pulls before refreshing.

**Which skills get installed is configuration, not a flag.** The `categories`
list in `src/dotfiles/resources/agents/skills.toml` selects them, and an empty
list — the default — installs all 562. Editing that list is acted on: `install`
prunes anything under the `bio-` namespace that is no longer selected. As a
command-line flag this could only ever add skills, never remove them, which is
why `--with` and `--allow-large` are gone.

Note the cost of the full catalogue: agents load every installed skill's name
and description to decide what to invoke, which is roughly **71,000 estimated
tokens** across all 562. Narrow `categories` if that proves too heavy.

Skills install as whole directories, so a skill's `usage-guide.md`, `examples/`
and `scripts/` come with it. Upstream already namespaces each skill with a
`bio-` prefix, and that declared name is used verbatim as the install directory
name — nothing rewrites the frontmatter.

Outside the Code Ocean capsule they are symlinks into the cache, so `update` is
a `git pull`. Inside the capsule they are real copies: capsule contents are
versioned and restored independently of `$HOME`, so a link into a cache there
would dangle after a rebuild.

`--dry-run` reports intended work without downloading or writing anything.

## Authoring rules

- Put cross-agent skills under `home/dot_claude/skills/`.
- Use only portable `name` and `description` frontmatter in `SKILL.md`.
- Put Codex-only UI metadata under `agents/openai.yaml`.
- Avoid Claude-specific substitutions in shared instructions. Refer to the
  directory containing `SKILL.md` as `<skill-dir>` when invoking bundled files.
- Keep detailed knowledge in direct `references/` links and deterministic work
  in `scripts/`.
- Validate every bundled skill before release.
