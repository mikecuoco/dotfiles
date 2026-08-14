# Claude Code integrations and skills

This guide covers the optional Claude Code setup commands. Run `dotfiles
doctor` after setup to inspect the resulting integration and skill state.

## Plugins and MCP servers

```bash
dotfiles claude setup [--with bioinformatics]... [--dry-run]
```

This command installs the default user-scoped Claude Code plugins and
configures their MCP servers. It is idempotent. `--dry-run` prints the work
without registering marketplaces, installing plugins, or altering MCP
configuration.

The default set includes GitHub, PubMed, Synapse, Context7, and Pyright LSP.
Add `--with bioinformatics` for bioRxiv, Open Targets, ToolUniverse,
scvi-tools, single-cell-rna-qc, Nextflow Development, and Scientific Problem
Selection. ToolUniverse must already be available on `PATH` before it can be
configured.

### Included integrations

| Group | Integrations |
|---|---|
| Default | GitHub, PubMed, Synapse, Context7, Pyright LSP |
| `bioinformatics` | bioRxiv, Open Targets, ToolUniverse, scvi-tools, single-cell-rna-qc, Nextflow Development, Scientific Problem Selection |

The 10x Genomics, ChEMBL, and Consensus life-sciences plugins are intentionally
not installed.

## Skills

```bash
dotfiles skills install [--with GROUP]... [--dry-run]
dotfiles skills update [--dry-run]
dotfiles skills status
```

`skills install` always installs bundled first-party skills and the default
GPTomics group. Add `--with spatial`, `--with genomics`, or `--with all` to
include additional groups; the option may be repeated. Downloaded source is
cached in `~/.local/share/dotfiles/bioskills`, and installed skills are placed
in `~/.claude/skills`.

`--dry-run` reports intended work without copying files or fetching the skills
repository. `skills update` refreshes bundled skills and every configured
GPTomics group. `skills status` is read-only and reports managed skills found
under `~/.claude/skills`.

```bash
# Default RNA-seq and single-cell skills plus spatial transcriptomics
dotfiles skills install --with spatial

# Refresh bundled skills and every GPTomics group
dotfiles skills update
```

## Authentication and ephemeral environments

Installation and authentication are separate. Plugins can be installed before
credentials are available, and `dotfiles doctor` reports outstanding auth
requirements.

| Service | Canonical environment variable | Alternative |
|---|---|---|
| Claude subscription OAuth | `CLAUDE_CODE_OAUTH_TOKEN` | `claude setup-token` |
| Anthropic API | `ANTHROPIC_API_KEY` | `claude auth login` |
| GitHub | `GH_TOKEN` | `gh auth login` |
| Synapse | `SYNAPSE_AUTH_TOKEN` | `synapse login` |
| Code Ocean API | `CODEOCEAN_API_TOKEN` | — |
| OpenAI API | `OPENAI_API_KEY` | — |
| Mem0 | `MEM0_API_KEY` | — |
| AWS | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | AWS profile or workload identity |

Set `CODEOCEAN_DOMAIN` for the non-secret Code Ocean host and
`AWS_DEFAULT_REGION` when needed. Never commit credentials: use gitignored
`~/.extra` locally or account Secrets in Code Ocean. Do not define
`ANTHROPIC_API_KEY` together with `CLAUDE_CODE_OAUTH_TOKEN`, because the API
key can override subscription OAuth. `ANTHROPIC_AUTH_TOKEN` is reserved for a
custom bearer-token gateway.

In a Codespace, Code Ocean capsule, or other ephemeral environment:

1. Install the package.
2. Run `dotfiles install`.
3. Run `dotfiles claude setup [--with bioinformatics]` when integrations are needed.
4. Provide the applicable credentials as environment secrets.

Plugin setup is independent of a scientific pipeline and may be omitted from a
reproducible capsule. Context7, Pyright LSP, basic PubMed access, and bundled
skills require no token. ToolUniverse authentication depends on the selected
tools.
