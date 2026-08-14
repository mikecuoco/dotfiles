# CLI reference

Run `dotfiles --help` for top-level usage, `dotfiles <command> --help` for a
command's options, and `dotfiles --version` for the installed package version.

## Install and update

```bash
dotfiles install [--profile PROFILE] [--dry-run] [--quiet] [--home DIR]
dotfiles update [--profile PROFILE] [--dry-run] [--quiet]
```

`install` installs the auto-detected profile into `~` unless `--home DIR` is
provided. It creates symlinks for managed files, regenerates composed
instruction files, and merges managed preferences into mutable JSON and TOML
files without replacing unrelated settings. An unmanaged destination is first
renamed to `<name>.dotfiles-backup.<UTC timestamp>`.

| Option | Meaning |
|---|---|
| `-p`, `--profile PROFILE` | Select `macos`, `linux`, `cluster`, `codeocean`, or `codespace` instead of automatic detection. |
| `-n`, `--dry-run` | Report changes without writing files or installer state. |
| `-q`, `--quiet` | Suppress routine progress; errors still print. |
| `--home DIR` | Install beneath another home directory; useful for tests or staging. |

`update` upgrades the package first, then runs `install` in a fresh Python
process so it applies the new resources. It uses `uv tool upgrade
mike-dotfiles` for a uv-tool installation and otherwise uses `pip` to upgrade
from GitHub. If upgrading fails, no configuration is applied. Its profile,
dry-run, and quiet options have the same meaning as `install`.

```bash
# See what the Code Ocean profile would change
dotfiles install --profile codeocean --dry-run

# Upgrade the package, then reinstall the detected profile
dotfiles update
```

## Inspection and health checks

```bash
dotfiles doctor [--json]
dotfiles status
dotfiles auth
```

`doctor` validates managed files and installer state, requires `git` and
`python3`, reports optional tools, checks credentials without exposing secret
values, and includes Claude integration and skill status where available. It
exits nonzero if the installation is missing or unhealthy, a required tool is
unavailable, or required Claude authentication is absent. `--json` emits the
same report in a machine-readable form.

`status` is a lightweight inventory. It prints the selected profile,
installation time, resource location, and the state of each installed path. It
exits nonzero when no installation state is present.

`auth` runs only credential checks. It recognizes Claude authentication from
environment variables or the Claude CLI; GitHub from `GH_TOKEN` or `gh`; and
optional Synapse, Code Ocean, AWS, OpenAI, and Mem0 credentials. It exits
nonzero only when required Claude authentication is missing.

## Shared project memory

```bash
dotfiles memory init [--repo DIR]
dotfiles memory list [--repo DIR] [--json]
dotfiles memory check [--repo DIR] [--json]
dotfiles memory migrate [--repo DIR] [--apply]
```

These commands manage the custom `.agents/memory/` convention shared by Claude
Code and Codex. `init` creates the directory safely, `list` reports filenames
and titles, and `check` validates the file contract and Git ignore behavior.
`migrate` reviews obsolete agent-specific locations; `--apply` copies only safe
candidates and never removes legacy files. See
[Shared project memory](project-memory.md).

## Profiles and instruction budgets

```bash
dotfiles profiles
dotfiles agent-stats
dotfiles claude-stats  # alias for agent-stats
```

`profiles` prints every profile with its description and inheritance chain.
See [Profiles](../README.md#profiles) for detection rules and installed
overlays.

`agent-stats` measures the composed instruction files for Claude and Codex,
including profile overlays. Its token counts are estimates (`words × 4/3`),
not results from a model tokenizer. It exits nonzero when the global
instruction budget (900 estimated tokens) or an overlay budget (500) is
exceeded.
