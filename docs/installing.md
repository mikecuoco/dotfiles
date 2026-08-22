# Installing and syncing

These dotfiles are managed entirely by [chezmoi](https://www.chezmoi.io), a
single static binary that needs no privileges and no Python. There is no
package to install.

## First-time bootstrap

chezmoi must be pointed at this repository once per machine:

```bash
chezmoi init --apply --promptString profile=codeocean \
    https://github.com/mikecuoco/dotfiles.git
```

`--promptString` keeps unattended bootstrap (Code Ocean capsules, CI) free of
interactive prompts. Omit it to be asked. From a local checkout, use
`chezmoi init --apply --source <path>` instead; the source directory is
remembered afterwards.

To install chezmoi and bootstrap in one step:

```bash
sh -c "$(curl -fsLS https://get.chezmoi.io)" -- init --apply mikecuoco
```

### Without root (HPC login nodes)

```bash
sh -c "$(curl -fsLS get.chezmoi.io)" -- -b "$HOME/.local/bin"
"$HOME/.local/bin/chezmoi" init --apply --promptString profile=cluster \
    https://github.com/mikecuoco/dotfiles.git
```

Call it by full path the first time: `~/.local/bin` only joins `PATH` once
`~/.exports` is installed, which is what this command is doing.

Two things the installer handles that matter on older login nodes. It checks
`ldd` and falls back to a fully static musl build when glibc is older than
2.35, so CentOS 7 (glibc 2.17) works. And chezmoi has a built-in git client, so
`init <repo>` does not require `git` on `PATH`.

## Day-to-day

| Command | What it does |
|---|---|
| `chezmoi apply` | Install the active profile. Symlinks managed files, regenerates composed instruction files, and merges managed preferences into mutable JSON and TOML without replacing unrelated settings. First-party agent skills are ordinary managed files, so they come with it. |
| `chezmoi update` | Pull the source repository, then apply. |
| `chezmoi apply --dry-run --verbose` | Report changes without writing anything. |
| `chezmoi status` | List managed files that differ from the target state. |
| `chezmoi diff` | Show exactly what an apply would change. |
| `chezmoi data` | Dump the template data, including the active profile and its layers. |
| `chezmoi doctor` | chezmoi's own health check. |
| `dotfiles-sync` | **Code Ocean only** — apply, then apply again into the capsule. See below. |
| `agents-memory-check` | Validate `.agents/memory/` in the current repository. See [Shared project memory](project-memory.md). |

Before the first apply on a machine, any unmanaged file chezmoi is about to
replace is copied to `<name>.dotfiles-backup.<UTC timestamp>`.

To select a profile explicitly, set `$DOTFILES_PROFILE` and re-init.
`promptStringOnce` caches its answer in chezmoi's persistent state, where
neither `init --promptString` nor `init --force` can reach it, so the
environment variable is the supported override:

```bash
DOTFILES_PROFILE=cluster chezmoi init && chezmoi apply
```

Valid profiles are `macos`, `linux`, `cluster`, `codeocean`, and `codespace`.
`common` is a composition layer, not something to install directly.

## Code Ocean: use `dotfiles-sync`, not `chezmoi apply`

Code Ocean splits the target state across two roots: shell dotfiles in `$HOME`,
agent configuration in the versioned capsule (`/root/capsule` by default,
overridable with `$DOTFILES_CAPSULE_DIR`). The capsule is restored on rebuild
*before* the dotfiles source is cloned back, so its contents must be real files
— a symlink into the source tree would dangle.

chezmoi writes one destination per invocation and has no per-path override, so
this needs a second pass with its own `--destination` and its own config
(`mode = "file"` instead of `"symlink"`). `dotfiles-sync` is that sequence:

```bash
dotfiles-sync            # both passes
dotfiles-sync --dry-run  # flags are forwarded to chezmoi apply
```

**On Code Ocean, plain `chezmoi apply` and `chezmoi update` only update `$HOME`
— the capsule is left untouched.** Use `dotfiles-sync` instead. Off Code Ocean
it is simply `chezmoi init && chezmoi apply`, so it is safe everywhere.

The second pass cannot be a chezmoi `run_` script: a script invoked during an
apply cannot itself run `chezmoi apply` without deadlocking on the
persistent-state lock.

`dotfiles-sync` is installed by the first apply, which makes a fresh capsule a
two-step bootstrap:

```bash
chezmoi init --apply --promptString profile=codeocean \
    https://github.com/mikecuoco/dotfiles.git
~/.local/bin/dotfiles-sync
```

## Checking your setup

There is no aggregate health command. The underlying tools report their own
state:

```bash
chezmoi doctor         # chezmoi's configuration and environment
chezmoi status         # managed files that have drifted
claude auth status     # Claude Code authentication
claude plugin list     # installed plugins and marketplaces
claude mcp list        # configured MCP servers
gh auth status         # GitHub
aws sts get-caller-identity   # AWS
```

See [Claude Code integrations](claude-tools.md) for what is expected to be
present and how credentials are supplied.

Agent instruction context budgets are enforced by the test suite rather than at
runtime — see [Agent context architecture](agent-context.md).
