# chezmoi migration spike — findings

Branch: `spike/chezmoi`. Scope: `linux` and `codeocean` profiles (which cover
`common` and `linux` layers transitively). The legacy Python installer is
untouched and still passing, so the two implementations can be diffed directly.

## Result

**Byte-level parity achieved** for both profiles, on clean and dirty
destinations, with one intentional structural difference (below).

```
$ scripts/parity-check.sh      # clean destinations + idempotency
$ scripts/parity-dirty.sh      # app-managed config + unmanaged file handling
```

| | legacy | chezmoi |
|---|---|---|
| plain dotfiles | symlink into repo | symlink into repo (`mode = "symlink"`) |
| `.claude/CLAUDE.md`, `.codex/AGENTS.md` | concatenated file | template — **byte-identical** |
| `.codex/config.toml` | marker-block merge | `modify_` template — **byte-identical**, comments/order/tables preserved |
| `.claude.json` | deep JSON merge | `modify_` template — **byte-identical**, mode 0600 |
| unmanaged file conflict | timestamped backup | timestamped backup (`run_once_before_` script) |
| re-apply | idempotent | idempotent (`chezmoi status` empty) |

## Size

185 lines of chezmoi config and templates — most of it comments; the executable
logic is roughly 60 lines — stand in for **1,421 lines** of `install.py`,
`profiles.py` and their tests. `agent_skills.py` (767) is not yet ported and
would shrink further via `.chezmoiexternal`.

## What the spike proved out

- `mode = "symlink"` reproduces link semantics, and deliberately skips templates
  and `modify_` files, so generated and merged files stay regular files — the
  three file kinds fall out of chezmoi's own rules instead of being dispatched
  by `group_links`.
- Profile inheritance flattens to a 13-line `.chezmoidata/profiles.toml` table,
  replacing `resolve_links`' recursive collect + dedup + orphan/conflict
  validation.
- The marker-block TOML merge — the risk flagged before starting — survives
  intact as a `modify_` template, including refusing to emit invalid TOML.

## What it cost

**1. Code Ocean needs two applies.** This is the significant finding.

chezmoi has no per-path destination. The natural expression — symlink
`~/.claude` into `/root/capsule` — **does not work**: chezmoi holds `.claude`
as a directory in its target state and replaces the symlink with a real
directory on every apply. Verified directly.

The workaround is a second apply with its own `--destination` and persistent
state, selected by `DOTFILES_CHEZMOI_SCOPE=capsule` in `.chezmoiignore`:

```sh
chezmoi apply                                          # $HOME
DOTFILES_CHEZMOI_SCOPE=capsule chezmoi apply --destination /root/capsule
```

This replaces ten lines of `install.py:_resolve_dst`. It works and is
idempotent, but it is *more* machinery than what it replaces, and it
reintroduces the shape of the bug the migration was meant to retire: two roots
that a reader can disagree with a writer about. Only two files actually need it
(`.claude/CLAUDE.md`, `.claude/settings.json`).

The split is gated on the capsule existing, mirroring `_capsule.is_dir()`, so
off-platform behaviour is unchanged.

**2. Nested `chezmoi` calls deadlock.** Calling `chezmoi` from inside a `run_`
script blocks forever on the persistent-state lock. The backup script therefore
derives target names from `CHEZMOI_SOURCE_DIR` in plain shell.

**3. chezmoi does not back up.** It overwrites unmanaged files silently. The
`run_once_before_05-backup-unmanaged.sh` script restores the legacy safety net
for the one moment it matters — first install onto a machine that already has
dotfiles.

**4. Auto-detection is gone.** Per decision, the profile is prompted via
`promptStringOnce` rather than detected. `--promptString` is keyed by prompt
*text*, so the prompt is literally `profile` to keep unattended bootstrap clean:
`chezmoi init --apply --promptString profile=codeocean <repo>`.

## Intentional behaviour change: `.vim` and matplotlib styles

Legacy symlinks the whole directory (`~/.vim -> repo/.../.vim`). chezmoi creates
a real directory of per-file symlinks.

This is an improvement, not a regression. Under the old scheme vim wrote its
runtime state *into the git repo* — `viminfo` was sitting untracked in
`src/dotfiles/resources/common/editor/.vim/` at the start of this audit. With
per-file symlinks, tracked config still resolves back to the repo (so `zg` spell
additions are still captured) while `viminfo`, `.VimballRecord`, `plugged/` and
`backups/` stay local.

Preserving the old shape is possible but requires moving the tree outside the
chezmoi source root and hand-writing a `symlink_` template — more machinery for
worse behaviour.

## Gotchas worth recording

- Empty files are dropped unless prefixed `empty_` (`.hushlogin`).
- Prefix order is type-then-attribute: `modify_private_dot_claude.json`.
- chezmoi appends a trailing newline to `modify_` template output.
- `common` is a composition layer, not an installable profile — the legacy
  installer rejects it, so parity is checked on `linux` and `codeocean`.

## Open before merging

- Port `macos`, `cluster`, `codespace`.
- Port skills — `.chezmoiexternal` `git-repo` should absorb the bioSkills clone
  in `agent_skills.py`.
- Decide the boundary with the Python CLI (`auth`, `claude`, `agent-stats`,
  `memory` have no chezmoi equivalent and should stay).
- Confirm chezmoi installs without root on the HPC login node.
- Decide whether the two-pass Code Ocean split is acceptable, or whether that
  single requirement justifies keeping the Python installer.
