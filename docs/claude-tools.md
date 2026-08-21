# Claude Code integrations

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

Shared Claude Code and Codex skills are documented in
[Agent skills](agent-skills.md).

## Authentication and ephemeral environments

Installation and authentication are separate. Plugins can be installed before
credentials are available, and `dotfiles doctor` reports outstanding auth
requirements.

| Service | Canonical environment variable | Alternative |
|---|---|---|
| Claude subscription OAuth ⭐ | `CLAUDE_CODE_OAUTH_TOKEN` | `claude setup-token` |
| GitHub | `GH_TOKEN` | Code Ocean `GIT_ACCESS_TOKEN` or `gh auth login` |
| Synapse | `SYNAPSE_AUTH_TOKEN` | `synapse login` |
| Code Ocean API | `CODEOCEAN_API_TOKEN` | — |
| OpenAI API | `OPENAI_API_KEY` | — |
| Mem0 | `MEM0_API_KEY` | — |
| AWS | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | AWS profile or workload identity |

Set `CODEOCEAN_DOMAIN` for the non-secret Code Ocean host and
`AWS_DEFAULT_REGION` when needed. Never commit credentials: use gitignored
`~/.extra` locally or account Secrets in Code Ocean.

**Claude authentication:** use `CLAUDE_CODE_OAUTH_TOKEN` (set via `claude
setup-token`) as the sole Claude credential. `~/.exports` actively runs
`unset ANTHROPIC_API_KEY` at shell startup, so the API key cannot shadow OAuth
even if it leaks in from the environment. If you previously set
`ANTHROPIC_API_KEY` as a Codespace Secret or in `~/.extra`, remove it there as
well. `ANTHROPIC_AUTH_TOKEN` is reserved for a custom bearer-token gateway and
should likewise not be set unless you are operating one.

In a Codespace, Code Ocean capsule, or other ephemeral environment:

1. Install the package.
2. Run `dotfiles install`.
3. Run `dotfiles claude setup [--with bioinformatics]` when integrations are needed.
4. Provide the applicable credentials as environment secrets.

Plugin setup is independent of a scientific pipeline and may be omitted from a
reproducible capsule. Context7, Pyright LSP, basic PubMed access, and bundled
skills require no token. ToolUniverse authentication depends on the selected
tools.
