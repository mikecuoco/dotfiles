# Dotfiles repository

- Package code lives under `src/dotfiles/`; bundled resources live under
  `src/dotfiles/resources/`.
- Treat files under user home directories as installed output. Change their
  resource sources and installer logic instead of editing installed copies.
- Preserve app-managed Claude and Codex configuration outside the dotfiles
  manager's explicitly owned files or merge markers.
- Keep shared agent behavior under `resources/common/agents/`; keep genuinely
  tool-specific behavior under `resources/common/claude/` or
  `resources/common/codex/`.
- Keep skills compatible with the Agent Skills `SKILL.md` directory format used
  by both Claude Code and Codex. Avoid tool-specific syntax in shared skills.
- Run relevant focused tests and the full test suite after installer, profile,
  instruction, or skill changes.
