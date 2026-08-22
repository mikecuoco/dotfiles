# Mike's dotfiles

[![tests](https://github.com/mikecuoco/dotfiles/actions/workflows/tests.yml/badge.svg)](https://github.com/mikecuoco/dotfiles/actions/workflows/tests.yml)

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
uv run --python '>=3.11' --with pytest pytest
```

There is nothing to install: the tests import only the standard library and
pytest, and the command above supplies both the runner and the Python 3.11+ that
`tomllib` needs. If pytest is already on your `PATH`, bare `pytest` works too.

The one requirement the command cannot supply is `chezmoi` on `PATH` — tests that
apply a profile skip without it. Note also that `uv run` reuses a virtualenv
found in the working directory or a parent when it satisfies `--python`, so a
stray `.venv` changes which interpreter you get.

`.github/workflows/tests.yml` runs that same command on `ubuntu-latest` and
`macos-latest` for every pull request, adding `--with ruamel.yaml` so the suite's
one optional import does not silently skip. Applying a profile is hermetic:
`$DOTFILES_SKIP_PACKAGE_INSTALL` (set by `tests/conftest.py`) stops each apply
from rerunning the package installer, which a throwaway `$HOME` would otherwise
trigger every time.

Dotfiles source lives in `home/` (the chezmoi root). Add or change a profile in
`home/.chezmoidata/profiles.toml`. Agent skills are in `home/dot_claude/skills/`
and are shared with Codex via `home/dot_agents/`. Managed helper commands are in
`home/dot_local/bin/`.
