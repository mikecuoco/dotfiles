# Profiles and configuration

## Profiles

Profiles inherit configuration from their parents. The detected profile can be
overridden with `dotfiles install --profile PROFILE`.

```text
common
├── macos        macOS / MacBook
├── linux        Generic Linux workstation or server
│   ├── cluster  HPC / SLURM / PBS / SGE clusters
│   ├── codeocean Code Ocean cloud workstation or container
│   └── codespace GitHub Codespaces
```

Detection uses the first matching signal:

| Detected by | Profile |
|---|---|
| `CODESPACES=true` or `GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN` | `codespace` |
| `CO_CAPSULE_ID`, `CO_PIPELINE_ID`, `CO_COMPUTATION_ID`, `CODEOCEAN_ENV`, or `CO_REPO_ID` | `codeocean` |
| `SLURM_JOB_ID`, `PBS_JOBID`, `SGE_TASK_ID`, `LSB_JOBID`, or a cluster-like hostname | `cluster` |
| Linux | `linux` |
| macOS | `macos` |

Run `dotfiles profiles` to print the available profiles and inheritance chains.

## Installed configuration

Every profile installs the following common configuration:

| Category | Files |
|---|---|
| Shell | `.bashrc`, `.bash_profile`, `.bash_prompt`, `.aliases`, `.exports`, `.functions`, `.inputrc` |
| Git | `.gitconfig`, `.gitignore`, `.gitattributes` |
| Editor | `.vimrc`, `.vim/` |
| Conda | `.condarc` |
| Misc | `.dircolors`, `.gemrc`, `.hushlogin` |
| Claude Code | `.claude/CLAUDE.md`, `.claude/settings.json` |
| Codex | `.codex/AGENTS.md`, a managed preference block in `.codex/config.toml` |

Profile overlays add the following paths:

| Profile | Extra files or settings |
|---|---|
| `macos` | `.aliases.macos`, `.exports.macos`, `.functions.macos`, `.conda_build_config.yaml`, Matplotlib styles |
| `linux` | `.exports.linux`, Matplotlib styles |
| `cluster` | `.exports.cluster`, `.functions.cluster`, `.Rprofile` |
| `codeocean` | `.exports.codeocean`, Code Ocean agent guidance, merged `.claude.json` defaults |
| `codespace` | `.exports.codespace` |

Shell overlays are sourced by `.bash_profile` at shell startup according to
the active profile saved at `~/.config/dotfiles/profile`.

## Installation behavior

Normal managed paths are symlinks. If an unmanaged destination already exists,
the installer renames it to `<name>.dotfiles-backup.<UTC timestamp>` before
linking the managed source. Re-running `dotfiles install` is idempotent.

The installer records the active profile, resource location, and installed
paths in `~/.config/dotfiles/state.json`; `dotfiles status` and `dotfiles
doctor` use this file to validate the installation.

Some destinations need to remain mutable:

- `append` generates an instruction file by concatenating the shared source,
  the tool-specific supplement, and any profile overlay.
- `merge-json` recursively adds the managed Code Ocean defaults to
  `~/.claude.json` while preserving account and runtime state.
- `merge-toml` adds a marker-owned `dotfiles` preference block to
  `~/.codex/config.toml` without replacing Codex-managed paths, plugins,
  notifications, or trusted-project state.

Both merge operations are atomic and preserve unrelated settings. The Codex
merge validates TOML and refuses symlink targets, malformed markers, and
unmanaged key collisions.

## Agent configuration

Claude and Codex derive their global instructions from the same canonical
preferences, plus small tool-specific supplements and any environment overlay.
This prevents shared working and safety guidance from drifting between tools.
See [Agent context architecture](agent-context.md) for the full hierarchy and
context-budget policy.
