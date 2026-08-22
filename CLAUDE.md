# Dotfiles repository

- Dotfiles live under `home/` and are installed by chezmoi, including agent
  skills (`home/dot_claude/skills/`) and the managed helper commands in
  `home/dot_local/bin/`. There is no Python package; `tests/` is the only Python.
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
  instruction, or skill changes: `uv run --python '>=3.11' --with pytest pytest`
  (append `-k <expr>` to focus). The repository is not an installable package, so
  `uv run` is what supplies pytest and a Python new enough for `tomllib`.
