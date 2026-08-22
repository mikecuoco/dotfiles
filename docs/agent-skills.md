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
install like any other managed file — `chezmoi apply` puts them in
`~/.claude/skills/`.

`~/.agents/skills` is a managed symlink to that directory, so Codex reads the
same tree. The two used to be independent copies kept in step by the installer;
linking them removes the possibility of drift and means anything writing skills
has one destination rather than two.

## Adding a skill

Create a directory under `home/dot_claude/skills/` and re-run `chezmoi apply`.

`tests/test_agent_skills.py` validates every shipped `SKILL.md`: the frontmatter
must parse, and its `name` must match the directory — a mismatch stops both
Claude Code and Codex loading the skill, silently. Run
`uv run --python '>=3.11' --with pytest pytest -k skill` after adding one.

> **Removed:** the GPTomics bioSkills integration (`dotfiles skills
> install|update|status`) was dropped, along with the `dotfiles` CLI itself. Installing the full catalogue cost
> roughly 71,000 estimated tokens of skill-discovery context across 562 skills,
> which every session paid for. The implementation is in git history if it is
> wanted again.

## Authoring rules

- Put cross-agent skills under `home/dot_claude/skills/`.
- Use only portable `name` and `description` frontmatter in `SKILL.md`.
- Put Codex-only UI metadata under `agents/openai.yaml`.
- Avoid Claude-specific substitutions in shared instructions. Refer to the
  directory containing `SKILL.md` as `<skill-dir>` when invoking bundled files.
- Keep detailed knowledge in direct `references/` links and deterministic work
  in `scripts/`.
- Validate every bundled skill before release.
