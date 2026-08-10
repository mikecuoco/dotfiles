# Mike's dotfiles

* I maintain this repo as *my* dotfiles, forked from the amazing [Paul Irish](https://github.com/paulirish)
* All bash awesomeness is from Paul
* `.spacemacs` has some inspiration from [gf3](https://github.com/gf3/dotfiles)

## my favorite parts.

### [`.aliases`](https://github.com/mikecuoco/dotfiles/blob/master/.aliases) and [`.functions`](https://github.com/mikecuoco/dotfiles/blob/master/.functions)

So many goodies.

### The "readline config" (`.inputrc`)
Basically it makes typing into the prompt amazing.

* tab like crazy for autocompletion that doesnt suck. tab all the things. srsly.
* no more <tab><tab> that says "Display all 1745 possibilities? (y or n)" YAY
* type `cat <uparrow>` to see your previous `cat`s and use them.
* case insensitivity.
* tab all the livelong day.

### Moving around in folders (`z`, `...`, `cdf`)
`z` helps you jump around to whatever folder. It uses actual real magic to determine where you should jump to. Seperately there's some `...` aliases to shorten `cd ../..` and `..`, `....` etc. Then, if you have a folder open in Finder, `cdf` will bring you to it.
```sh
z dotfiles
z blog
....      # drop back equivalent to cd ../../..
z public
cdf       # cd to whatever's up in Finder
```
`z` learns only once its installed so you'll have to cd around for a bit to get it taught.
Lastly, I use `open .` to open Finder from this path. (That's just available normally.)


## overview of files

####  Automatic config
* `.vimrc`, `.vim` - vim config, obv.
* `.inputrc` - behavior of the actual prompt line

#### shell environment
* `.aliases`
* `.bash_profile`
* `.bash_prompt`
* `.bashrc`
* `.exports`
* `.functions`
* `.extra` - not included, explained below

#### manual run
* `setup-a-new-machine.sh` - random apps i need installed
* `symlink-setup.sh`  - sets up symlinks for all dotfiles and vim config.
* `brew.sh` & `brew-cask.sh` - homebrew initialization

#### git, brah
* `.git`
* `.gitattributes`
* `.gitconfig`
* `.gitignore`


### `.extra` for private configuration

There will be items that don't belong to be committed to a git repo, because either 1) it shoudn't be the same across your machines or 2) it shouldn't be in a git repo. Kick it off like this:

`touch ~/.extra && $EDITOR $_`

I have some EXPORTS, my PATH construction, and a few aliases for ssh'ing into my servers in there.

I don't know how other folks manage their $PATH, but this is how I do mine:

```shell
# The top-most paths override here.
      PATH=/opt/local/bin
PATH=$PATH:/opt/local/sbin
PATH=$PATH:/bin
PATH=$PATH:~/.rvm/bin
PATH=$PATH:~/code/git-friendly
# ...

export PATH
```


### Sensible OS X defaults

Mathias's repo is the canonical for this, but you should probably run his or mine after reviewing it.

```bash
./.macos.sh
```

### Syntax highlighting for these files

If you edit this stuff, install [Dotfiles Syntax Highlighting](https://github.com/mattbanks/dotfiles-syntax-highlighting-st2) via [Package Control](http://wbond.net/sublime_packages/package_control)

### 2020 update

Rust folks have made a few things that are changing things.

 - https://github.com/bigH/git-fuzzy interactive git thing. deprecates my `git recent` script. and probably some other things.

 also interested in https://github.com/dandavison/open-in-editor

## Claude Code integration

The dotfiles install a global `~/.claude/CLAUDE.md` (universal working-style
rules, kept deliberately small) and, for environment-specific profiles such as
Code Ocean, an appended overlay with environment invariants.

The context architecture follows a progressive-disclosure hierarchy:
global → profile overlay → project CLAUDE.md → rules/skills → auto-memory.

See [`docs/claude-context.md`](docs/claude-context.md) for the full design,
memory policy, and how to check context budgets with `dotfiles claude-stats`.

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

| Integration | Auth required | How to authenticate |
|-------------|--------------|---------------------|
| GitHub | Yes | `gh auth login` or set `GH_TOKEN` |
| Synapse | Yes | `synapse login` or set `SYNAPSE_AUTH_TOKEN` |
| Context7 | No | — |
| Pyright LSP | No | — |
| PubMed | No (for basic use) | — |
| ToolUniverse | Depends | See [ToolUniverse docs](https://zitniklab.hms.harvard.edu/ToolUniverse/) |
| Bioinformatics plugins | No | — |

Credentials are never stored in this repository. Place secrets in `~/.extra`
(which is gitignored) and export them from your shell profile.

> **Note on claude.ai connectors:** PubMed, Synapse, bioRxiv, and Open Targets
> also auto-sync to Claude Code when you are logged in at [claude.ai]. The plugin
> versions installed above work with API-key auth and in environments without a
> claude.ai session.

#### Ephemeral environments (Codespaces, Code Ocean, containers)

1. Install the package: `uv tool install git+https://github.com/mikecuoco/dotfiles`
2. Install dotfiles: `dotfiles install`
3. Install Claude plugins: `dotfiles claude setup [--with bioinformatics]`
4. Authenticate: set `GH_TOKEN`, `SYNAPSE_AUTH_TOKEN`, etc. in the environment

Plugin setup is independent of the scientific computational pipeline. Code Ocean
capsules may omit it entirely; it should not affect pipeline reproducibility.

For ToolUniverse, the `tooluniverse` binary must be installed separately before
`dotfiles claude setup --with bioinformatics` can configure it as an MCP server.
See the [ToolUniverse documentation](https://zitniklab.hms.harvard.edu/ToolUniverse/)
for current installation instructions.

## TO-DO 

- [ ] add git configuration
- [ ] test `tunnel()`
- [ ] add `check_tunnel()`


