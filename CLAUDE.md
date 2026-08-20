# Dotfiles repository

- Dotfiles live under `home/` and are installed by chezmoi, including agent
  skills (`home/dot_claude/skills/`). `src/dotfiles/` is the CLI that wraps
  chezmoi, plus the Claude plugin config it reads.
- Treat files under user home directories as installed output. Change the
  source under `home/` rather than editing installed copies.
- Preserve app-managed Claude and Codex configuration outside the dotfiles
  manager's explicitly owned files or merge markers.
- Keep shared agent behavior in `home/.chezmoitemplates/agents-preferences.md`;
  keep genuinely tool-specific behavior in `claude-instructions.md` or
  `codex-instructions.md` alongside it.
- Keep skills compatible with the Agent Skills `SKILL.md` directory format used
  by both Claude Code and Codex. Avoid tool-specific syntax in shared skills.
- Run relevant focused tests and the full test suite after installer, profile,
  instruction, or skill changes.
