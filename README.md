# Mike's dotfiles

A cross-platform dotfiles manager for macOS, Linux, HPC clusters, GitHub Codespaces, and Code Ocean — packaged as a Python CLI so installation is a single command anywhere Python is available.

## Quick start

```bash
# Install globally with uv (recommended)
uv tool install git+https://github.com/mikecuoco/dotfiles

# Or in development
git clone https://github.com/mikecuoco/dotfiles && cd dotfiles
pip install -e .

# Install dotfiles for the detected platform
dotfiles install

# Preview changes without touching anything
dotfiles install --dry-run
```

## CLI reference

```
dotfiles install   [-p PROFILE] [-n/--dry-run] [--home DIR]
dotfiles doctor    [--json]
dotfiles status
dotfiles auth
dotfiles profiles
dotfiles skills     install|update|status [--with GROUP]
```

| Command | What it does |
|---|---|
| `install` | Symlink dotfiles for the active (or specified) profile; backs up any existing files |
| `doctor` | Check that all installed symlinks and generated files are healthy |
| `status` | Show what's currently installed and which profile is active |
| `auth` | Report authentication status (Anthropic, GitHub, AWS, Mem0) |
| `profiles` | List all available profiles with descriptions |
| `skills` | Install bundled first-party and selected GPTomics skills for Claude Code |

## Profiles

Profiles compose via inheritance — each child inherits all of its parent's links and can override or append to them.

```
common
├── macos        macOS / MacBook
├── linux        Generic Linux workstation or server
│   ├── cluster  HPC / SLURM / PBS / SGE clusters
│   ├── codeocean Code Ocean cloud workstation or container
│   └── codespace GitHub Codespaces
```

The active profile is **auto-detected** at install time (override with `--profile`):

| Detected by | Profile |
|---|---|
| `CODESPACES=true` or `GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN` | `codespace` |
| `CODEOCEAN_ENV` or `CO_REPO_ID` | `codeocean` |
| `SLURM_JOB_ID`, `PBS_JOBID`, `SGE_TASK_ID`, `LSB_JOBID`, or cluster-like hostname | `cluster` |
| `uname = Linux` | `linux` |
| `uname = Darwin` | `macos` |

## What gets installed

### Common (all platforms)

| Category | Files |
|---|---|
| Shell | `.bashrc`, `.bash_profile`, `.bash_prompt`, `.aliases`, `.exports`, `.functions`, `.inputrc` |
| Git | `.gitconfig`, `.gitignore`, `.gitattributes` |
| Editor | `.vimrc`, `.vim/` |
| Conda | `.condarc` |
| Misc | `.dircolors`, `.gemrc`, `.hushlogin` |
| Claude Code | `.claude/CLAUDE.md`, `.claude/settings.json` |

### Plugin and MCP server setup

After installing dotfiles, run the Claude setup command to install managed
plugins and MCP servers:

```bash
# Install core integrations (works on all platforms)
dotfiles claude setup

# Also install bioinformatics/life-science integrations
dotfiles claude setup --with bioinformatics

# Preview without installing
dotfiles claude setup --dry-run
dotfiles claude setup --with bioinformatics --dry-run
```

`dotfiles doctor` reports the status of each integration after setup.

### Claude Code skills

First-party skills are versioned under `src/dotfiles/resources/claude/skills/`
and copied to `~/.claude/skills/` on each workstation. The repository remains
the source of truth; a small installation registry prevents bundled updates
from overwriting an unmanaged skill with the same name.

The bundled `code-ocean-capsule` skill provides numbered, analysis-arm-based
capsule conventions, `/scratch`-first runtime storage, dataset/API provenance
refresh, Conda locking guidance, and a non-executing reproducibility checker.

```bash
# Install bundled skills plus the default GPTomics groups
dotfiles skills install

# Preview without writing or fetching
dotfiles skills install --dry-run

# Refresh bundled and downloaded skills
dotfiles skills update

# Show installed first-party and GPTomics skills
dotfiles skills status
```

#### Default integrations

Installed on all supported environments (macOS, Linux, Codespaces, Code Ocean,
HPC/cluster):

| Integration | Type | Purpose |
|-------------|------|---------|
| **GitHub** | Plugin | Repository access, issues, PRs via the GitHub MCP server |
| **PubMed** | Plugin | Biomedical literature search (NCBI) |
| **Synapse** | Plugin | Sage Bionetworks collaborative data platform |
| **Context7** | MCP server | Up-to-date library documentation (no auth required) |
| **Pyright LSP** | Plugin | Python type checking and in-editor diagnostics |

#### Bioinformatics integrations

Installed with `--with bioinformatics`:

| Integration | Type | Purpose |
|-------------|------|---------|
| **bioRxiv** | Plugin | bioRxiv/medRxiv preprint search |
| **Open Targets** | Plugin | Gene–disease–drug association platform |
| **ToolUniverse** | MCP server | 600+ scientific bioinformatics tools (Harvard Zitnik Lab) |
| **scvi-tools** | Plugin (skill) | scVI, scANVI, totalVI, PeakVI, MultiVI workflow skills |
| **single-cell-rna-qc** | Plugin (skill) | MAD-based quality filtering workflow skills |
| **Nextflow Development** | Plugin (skill) | nf-core pipeline execution skills |
| **Scientific Problem Selection** | Plugin (skill) | Research ideation and risk assessment skills |

#### Intentionally not installed

The following life-sciences plugins are available but are **not installed**:

- **10x Genomics** — not needed for this workflow
- **ChEMBL** — not needed for this workflow
- **Consensus** — not needed for this workflow

#### Authentication

Installation and authentication are separate steps. Plugins install regardless
of auth status; doctor reports any outstanding auth requirements.

| Credential | Canonical environment variable | Alternative |
|------------|--------------------------------|-------------|
| Claude subscription OAuth | `CLAUDE_CODE_OAUTH_TOKEN` | Generate with `claude setup-token` |
| Anthropic API key | `ANTHROPIC_API_KEY` | `claude auth login` for interactive use |
| GitHub | `GH_TOKEN` | `gh auth login` |
| Synapse | `SYNAPSE_AUTH_TOKEN` | `synapse login` |
| Code Ocean API | `CODEOCEAN_API_TOKEN` | — |
| OpenAI API | `OPENAI_API_KEY` | — |
| Mem0 | `MEM0_API_KEY` | — |
| AWS access key | `AWS_ACCESS_KEY_ID` | AWS profile or workload identity |
| AWS secret key | `AWS_SECRET_ACCESS_KEY` | AWS profile or workload identity |
| AWS temporary session | `AWS_SESSION_TOKEN` | Only for temporary credentials |

Set the non-secret Code Ocean host or URL in `CODEOCEAN_DOMAIN`, and the AWS
region in `AWS_DEFAULT_REGION` when a tool cannot infer it.

Credentials are never stored in this repository. On a local machine, place
exports in `~/.extra` (which is gitignored). In Code Ocean, create account
Secrets with the exact canonical names above; do not add them to a capsule's
environment recipe, Dockerfile, or committed shell configuration.

Use `CLAUDE_CODE_OAUTH_TOKEN` for the token produced by `claude setup-token`.
`ANTHROPIC_AUTH_TOKEN` is reserved for a custom bearer-token gateway, not normal
Claude subscription OAuth. Avoid defining `ANTHROPIC_API_KEY` and
`CLAUDE_CODE_OAUTH_TOKEN` together because the API key can override subscription
authentication.

Context7, Pyright LSP, basic PubMed access, and the bundled bioinformatics
skills do not require tokens. ToolUniverse authentication depends on the tools
enabled in a particular workflow.

> **Note on claude.ai connectors:** PubMed, Synapse, bioRxiv, and Open Targets
> also auto-sync to Claude Code when you are logged in at [claude.ai]. The plugin
> versions installed above work with API-key auth and in environments without a
> claude.ai session.

#### Ephemeral environments (Codespaces, Code Ocean, containers)

1. Install the package: `uv tool install git+https://github.com/mikecuoco/dotfiles`
2. Install dotfiles: `dotfiles install`
3. Install Claude plugins: `dotfiles claude setup [--with bioinformatics]`
4. Authenticate with the canonical environment variables listed above

Plugin setup is independent of the scientific computational pipeline. Code Ocean
capsules may omit it entirely; it should not affect pipeline reproducibility.

For ToolUniverse, the `tooluniverse` binary must be installed separately before
`dotfiles claude setup --with bioinformatics` can configure it as an MCP server.
See the [ToolUniverse documentation](https://zitniklab.hms.harvard.edu/ToolUniverse/)
for current installation instructions.

### Platform overlays

Each profile adds files alongside the common ones. Shell overlays (`.exports.<profile>`, `.aliases.<profile>`, `.functions.<profile>`) are sourced automatically by `.bash_profile` at shell startup.

| Profile | Extra files |
|---|---|
| `macos` | `.aliases.macos`, `.exports.macos`, `.functions.macos`, `.conda_build_config.yaml` |
| `linux` | `.exports.linux` |
| `cluster` | `.exports.cluster`, `.functions.cluster`, `.Rprofile` |
| `codeocean` | `.exports.codeocean`, `.claude/CLAUDE.md` (appended to common) |
| `codespace` | `.exports.codespace` |

### Profile overlays (`append` mode)

A link declared with `mode = "append"` concatenates its source onto the parent's file rather than replacing it. This is used for profile-specific `CLAUDE.md` additions — the `codeocean` profile appends its own instructions to the common `CLAUDE.md` to produce a single merged file.

## How it works

1. **`dotfiles install`** resolves the full link list for the active profile (depth-first through `inherits`), then either symlinks each file into `$HOME` or — when append entries exist for a destination — writes a concatenated regular file.
2. **Backup on conflict**: if a file already exists at the destination it is renamed to `<name>.dotfiles-backup.<timestamp>` before being replaced.
3. **Idempotent**: re-running `install` is safe; unchanged symlinks and up-to-date generated files are skipped.
4. **State file**: installation details are saved to `~/.config/dotfiles/state.json` so `status` and `doctor` can verify the installation without re-reading the package.
5. **Active profile**: written to `~/.config/dotfiles/profile` and read by `.bash_profile` to source the right platform overlays at shell startup.

## Extending or developing

```bash
git clone https://github.com/mikecuoco/dotfiles
cd dotfiles
pip install -e .

# Run tests
pytest

# Preview what a specific profile would install
dotfiles install --profile cluster --dry-run
```

Resources live in `src/dotfiles/resources/`, organized by profile name. Add a new profile by editing `src/dotfiles/resources/profiles.toml`.

## macOS setup scripts

The following scripts in `src/dotfiles/resources/macos/setup/` are meant to be run manually on a fresh machine:

```bash
./brew.sh        # core Homebrew formulae
./brew-cask.sh   # GUI applications via Homebrew Cask
./macos.sh       # sensible macOS defaults
```

## HPC cluster extras

`src/dotfiles/resources/cluster/setup/` contains helper scripts for cluster environments:

- `conda-setup.sh` — bootstrap conda on a cluster
- `singularity-setup.sh` — Singularity / Apptainer configuration
