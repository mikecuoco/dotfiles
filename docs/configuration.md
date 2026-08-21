# Profiles and configuration

## Profiles

Profiles inherit configuration from their parents. The layer table lives in
`home/.chezmoidata/profiles.toml`, and `home/.chezmoiignore` excludes anything
outside the active profile's layers. The profile can be set with
`dotfiles install --profile PROFILE`, and is auto-detected only on first run.

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
| `macos` | `.aliases.macos`, `.exports.macos`, `.functions.macos`, `.conda_build_config.yaml` |
| `linux` | `.exports.linux` |
| `cluster` | `.exports.cluster`, `.functions.cluster`, `.Rprofile` |
| `codeocean` | `.exports.codeocean`, Code Ocean agent guidance, merged `.claude.json` defaults |
| `codespace` | `.exports.codespace` |

Shell overlays are sourced by `.bash_profile` at shell startup according to
the active profile, which chezmoi writes to `~/.config/dotfiles/profile`.
`$DOTFILES_PROFILE` overrides both the file and the chezmoi config.

## Installation behavior

Installation is [chezmoi](https://www.chezmoi.io) in `mode = "symlink"`, driven
from `home/` at the repository root. The three kinds of managed file fall out
of chezmoi's own naming rules rather than being dispatched by hand:

| Source form | Result | Replaces |
|---|---|---|
| plain file, e.g. `dot_bashrc` | symlink into the source tree | `mode = "link"` |
| `*.tmpl`, e.g. `dot_claude/CLAUDE.md.tmpl` | generated regular file | `mode = "append"` |
| `modify_*`, e.g. `dot_codex/modify_config.toml` | merged regular file | `mode = "merge-json"` / `"merge-toml"` |

Composed and merged targets are deliberately regular files, not symlinks: an
app writing to `~/.codex/config.toml` must not write into the git checkout.

Re-running `dotfiles install` is idempotent — `chezmoi status` is empty
afterwards, which `dotfiles status` and `dotfiles doctor` both report on.
There is no installer state file; chezmoi compares its target state against
the destination directly, so no manifest can drift out of sync with reality.

Destinations that must stay mutable:

- `~/.claude.json` — the managed Code Ocean defaults are set by path, leaving
  account and runtime state untouched.
- `~/.codex/config.toml` — a marker-delimited `dotfiles` block is merged in
  without replacing Codex-managed paths, plugins, notifications, or
  trusted-project state. Comments, key order and tables outside the block are
  preserved byte for byte, and the result is validated as TOML before it is
  written.

Before the first apply on a machine, `run_once_before_05-backup-unmanaged.sh`
copies any unmanaged file that is about to be replaced to
`<name>.dotfiles-backup.<UTC timestamp>`. chezmoi otherwise overwrites
silently. Only leaf targets are considered, so directories such as `~/.config`
are never copied wholesale.

### Two known deviations

`~/.vim` and the Matplotlib stylelib become real directories of per-file
symlinks rather than single directory symlinks. This is deliberate: under the
old scheme vim wrote its runtime state (`viminfo`, `.VimballRecord`,
`plugged/`) straight into the git repository. Tracked config still resolves
back to the repo, while runtime state stays local.

Profile-specific git credential helpers are written to `~/.gitconfig.profile`
and pulled in by an `[include]` in the managed `~/.gitconfig`. The previous
installer ran `git config --global`, which — because `~/.gitconfig` is a
symlink into the repository — wrote its output into the tracked source file.

## Agent configuration

Claude and Codex derive their global instructions from the same canonical
preferences, plus small tool-specific supplements and any environment overlay.
This prevents shared working and safety guidance from drifting between tools.
See [Agent context architecture](agent-context.md) for the full hierarchy and
context-budget policy.

## Working on the chezmoi source

Everything under `home/` is chezmoi's source tree. A few of its rules are easy
to trip over:

- Files whose name begins with `.` are chezmoi's own and are never installed.
  That is what makes `.chezmoitemplates/` usable for instruction fragments, but
  it also means a genuine dotfile must be named `dot_foo`, not `.foo`.
- Empty files are dropped unless prefixed `empty_` (hence `empty_dot_hushlogin`).
- Prefix order is type, then attribute: `modify_private_dot_claude.json`.
- chezmoi appends a trailing newline to `modify_` template output, so those
  templates should not emit one themselves.
- `chezmoi execute-template --init` treats its input as a *config* template and
  does not load `.chezmoitemplates`. To render a file that composes fragments,
  render the config first and pass it with `--config`.
- Calling `chezmoi` from inside a `run_` script deadlocks on the persistent
  state lock. Scripts derive what they need from `$CHEZMOI_SOURCE_DIR` instead.
- `promptStringOnce` caches its answer in the persistent state, where neither
  `init --promptString` nor `init --force` can change it. `$DOTFILES_PROFILE` is
  the supported override and is what `--profile` sets.

The `cluster` profile assumes no root: see
[the CLI reference](cli-reference.md#without-root-hpc-login-nodes) for the
rootless bootstrap, and note that the Python CLI is optional there.

Verify changes with the full suite; `tests/test_chezmoi_render.py` applies every
profile into a throwaway destination and checks the results and idempotency.
