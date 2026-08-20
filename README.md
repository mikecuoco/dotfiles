# Mike's dotfiles

A cross-platform dotfiles manager for macOS, Linux, HPC clusters, GitHub
Codespaces, and Code Ocean. It is packaged as a Python CLI, so installation is
one command wherever Python 3.8+ is available.

## Quick start

```bash
# Install globally with uv (recommended)
uv tool install git+https://github.com/mikecuoco/dotfiles

# Or install a development checkout
git clone https://github.com/mikecuoco/dotfiles && cd dotfiles
pip install -e .

# Install the automatically detected profile
dotfiles install

# Preview changes, check health, or upgrade and reapply configuration
dotfiles install --dry-run
dotfiles doctor
dotfiles update
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

Resources live in `src/dotfiles/resources/`. Add or change a profile in
`home/.chezmoidata/profiles.toml`.

Fresh-machine setup scripts are in `src/dotfiles/resources/macos/setup/`.
Cluster helpers are in `src/dotfiles/resources/cluster/setup/`.
