# CLI reference

Run `dotfiles --help` for top-level usage, `dotfiles <command> --help` for a
command's options, and `dotfiles --version` for the installed package version.

## Install and update

### First-time bootstrap

Dotfiles are installed by [chezmoi](https://www.chezmoi.io), which must be
pointed at this repository once per machine:

```bash
chezmoi init --apply --promptString profile=codeocean \
    https://github.com/mikecuoco/dotfiles.git
```

`--promptString` keeps unattended bootstrap (Code Ocean capsules, CI) free of
interactive prompts. Omit it to be asked. From a local checkout, use
`chezmoi init --apply --source <path>` instead; the source directory is
remembered afterwards.

### Day-to-day

```bash
dotfiles install [--profile PROFILE] [--dry-run] [--quiet] [--refresh]
dotfiles update [--profile PROFILE] [--dry-run] [--quiet]
```

`install` applies the active profile: symlinks for managed files, regenerated
composed instruction files, and managed preferences merged into mutable JSON
and TOML without replacing unrelated settings. It then installs the bundled
agent skills. Before the first apply on a machine, any unmanaged file it is
about to replace is copied to `<name>.dotfiles-backup.<UTC timestamp>`.

| Option | Meaning |
|---|---|
| `-p`, `--profile PROFILE` | Select `macos`, `linux`, `cluster`, `codeocean`, or `codespace`. Without it the configured profile is kept, or auto-detected on first run. |
| `-n`, `--dry-run` | Report changes without writing anything. |
| `-q`, `--quiet` | Suppress routine progress; errors still print. |
| `--refresh` | Pull the dotfiles source repository before applying. |

On Code Ocean, `install` applies twice: once to `$HOME`, then once to
`/root/capsule` for the agent configuration that must survive a capsule
rebuild. chezmoi has no per-path destination, so this is a second pass with its
own `--destination`.

`update` upgrades the package first, then runs `install --refresh` in a fresh
Python process so both the code and the dotfiles come from the new version. It
uses `uv tool upgrade mike-dotfiles` for a uv-tool installation and otherwise
uses `pip` to upgrade from GitHub. If upgrading fails, no configuration is
applied.

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

`doctor` asks chezmoi which managed files are out of date, requires `git` and
`python3`, reports optional tools, checks credentials without exposing secret
values, and includes Claude integration and skill status where available. It
exits nonzero if the installation is missing or unhealthy, a required tool is
unavailable, or required Claude authentication is absent. `--json` emits the
same report in a machine-readable form.

`status` prints the active profile, the chezmoi source directory, and anything
apply would change. It exits nonzero when nothing is installed or when managed
files have drifted.

`auth` runs only credential checks. It recognizes Claude authentication from
environment variables or the Claude CLI; GitHub from `GH_TOKEN`, Code Ocean's
`GIT_ACCESS_TOKEN`, or `gh`; and
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

`profiles` prints every profile with its description and inherited layers,
marking the active one. The list comes from `home/.chezmoidata/profiles.toml`.
See [Profiles](../README.md#profiles) for detection rules and installed
overlays.

`agent-stats` renders the composed instruction files for Claude and Codex with
chezmoi -- the exact bytes that get installed -- for every profile. Its token counts are estimates (`words × 4/3`),
not results from a model tokenizer. It exits nonzero when the global
instruction budget (900 estimated tokens) or an overlay budget (500) is
exceeded.
