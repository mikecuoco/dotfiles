# Mike's dotfiles

Cross-platform dotfiles for macOS, Linux, HPC clusters, GitHub Codespaces, and
Code Ocean. They are managed by [chezmoi](https://www.chezmoi.io), a single
static binary — no Python, and no root required.

## Quick start

```bash
# to install for the first time
sh -c "$(curl -fsLS https://get.chezmoi.io)" -- init --apply mikecuoco

# to sync with the remote
chezmoi update
```

On Code Ocean, use `dotfiles-sync` instead of `chezmoi apply`/`chezmoi update`:
agent configuration lives in the versioned capsule, which needs a second pass.
See [Installing and syncing](docs/installing.md).

## Documentation

- [Installing and syncing](docs/installing.md) — bootstrap, day-to-day commands, rootless install, Code Ocean.
- [Profiles and configuration](docs/configuration.md) — detection, installed files, overlays, and merge behavior.
- [Agent skills](docs/agent-skills.md) — shared Claude Code and Codex skills.
- [Claude Code integrations](docs/claude-tools.md) — plugins, MCP servers, and authentication.
- [Agent context architecture](docs/agent-context.md) — shared Claude/Codex instructions and context policy.
- [Shared project memory](docs/project-memory.md) — local, cross-agent project discoveries and validation.

## Development

```bash
git clone https://github.com/mikecuoco/dotfiles
cd dotfiles
pytest
```

Nothing to install: the tests import only the standard library and pytest.
They need `chezmoi` on `PATH` (tests that apply profiles skip without it) and
Python 3.11+ for `tomllib`.

Dotfiles source lives in `home/` (the chezmoi root). Add or change a profile in
`home/.chezmoidata/profiles.toml`. Agent skills are in `home/dot_claude/skills/`
and are shared with Codex via `home/dot_agents/`. Managed helper commands are in
`home/dot_local/bin/`.
