# Mike's dotfiles

A cross-platform dotfiles manager for macOS, Linux, HPC clusters, GitHub
Codespaces, and Code Ocean. It is packaged as a Python CLI, so installation is
one command wherever Python 3.8+ is available.

## Quick start

```bash
# 1. Install chezmoi (required — dotfiles are applied by chezmoi)
brew install chezmoi                                       # macOS
# or: sh -c "$(curl -fsLS get.chezmoi.io)" -- -b ~/.local/bin

# 2. Install the dotfiles CLI
uv tool install git+https://github.com/mikecuoco/dotfiles

# 3. Bootstrap chezmoi (once per machine)
chezmoi init --apply https://github.com/mikecuoco/dotfiles.git

# Re-apply, preview changes, check health, or upgrade and reapply
dotfiles install
dotfiles install --dry-run
dotfiles doctor
dotfiles update
```

For a development checkout:

```bash
git clone https://github.com/mikecuoco/dotfiles && cd dotfiles
pip install -e .
chezmoi init --source .   # point chezmoi at the local checkout
dotfiles install
```

For legacy images that require `setup.py develop`, install `setuptools` first:

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e git+https://github.com/mikecuoco/dotfiles.git#egg=mike-dotfiles
```

For deployed environments such as Code Ocean capsules, prefer the
non-editable install:

```bash
python -m pip install git+https://github.com/mikecuoco/dotfiles.git
```

## Documentation

- [CLI reference](docs/cli-reference.md) — install, update, checks, profiles, and context budgets.
- [Profiles and configuration](docs/configuration.md) — detection, installed files, overlays, and merge behavior.
- [Agent skills](docs/agent-skills.md) — shared Claude Code and Codex skills.
- [Claude Code integrations](docs/claude-tools.md) — plugins, MCP servers, and authentication.
- [Agent context architecture](docs/agent-context.md) — shared Claude/Codex instructions and context policy.
- [Shared project memory](docs/project-memory.md) — local, cross-agent project discoveries and validation.

## Development

```bash
git clone https://github.com/mikecuoco/dotfiles
cd dotfiles
pip install -e .
pytest
```

Dotfiles source lives in `home/` (the chezmoi root). Add or change a profile in
`home/.chezmoidata/profiles.toml`. Agent skills are in `home/dot_claude/skills/`
and are shared with Codex via `home/dot_agents/`.

Python CLI resources live in `src/dotfiles/resources/`. Fresh-machine macOS setup
scripts are in `scripts/setup/`.
