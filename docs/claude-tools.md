# Claude Code integrations

## Plugins and marketplaces

Plugins are **declared, not installed by a script.** They live in
`home/dot_claude/settings.json`, which chezmoi installs as `~/.claude/settings.json`:

```json
"enabledPlugins": {
  "github@claude-plugins-official": true,
  "pubmed@life-sciences": true,
  "synapse@life-sciences": true,
  "pyright-lsp@claude-plugins-official": true
},
"extraKnownMarketplaces": {
  "life-sciences": { "source": { "source": "github", "repo": "anthropics/life-sciences" } }
}
```

To add or remove a plugin, edit that file and `chezmoi apply`. Claude Code reads
the declaration itself — there is nothing to run.

| Plugin | Marketplace | Purpose |
|---|---|---|
| `github` | `claude-plugins-official` | GitHub repository, issue, and PR access |
| `pyright-lsp` | `claude-plugins-official` | Python type checking and in-editor diagnostics. Requires `npm install -g pyright`. |
| `pubmed` | `life-sciences` | PubMed literature search and retrieval |
| `synapse` | `life-sciences` | Synapse data platform access. Needs `~/.synapseConfig` or `SYNAPSE_AUTH_TOKEN` to authenticate. |

Verify what actually loaded with `claude plugin list` and `claude mcp list`.

### Life-science integrations not enabled here

Available in the `life-sciences` marketplace but deliberately left out:
`10x-genomics`, `consensus`, `chembl` (claude.ai connector only), `biorxiv`,
`open-targets`, `scvi-tools`, `single-cell-rna-qc`, `nextflow-development`,
`scientific-problem-selection`.

Most are reachable as **claude.ai connectors** when signed in at claude.ai —
PubMed, Synapse, bioRxiv, Open Targets, ChEMBL, and Consensus all auto-sync to
Claude Code that way, with no local configuration. Enable a plugin version only
where claude.ai OAuth is unavailable. To enable one, add it to `enabledPlugins`.

### Local MCP servers

None are configured. Two were previously registered by the removed
`dotfiles claude setup` command, and both are reachable another way:

- **Context7** — documentation lookup; add with
  `claude mcp add --transport http --scope user context7 https://mcp.context7.com/mcp`
- **ToolUniverse** — 600+ scientific tools (Harvard Zitnik Lab); needs the
  `tooluniverse` binary on `PATH` first, then
  `claude mcp add --transport stdio --scope user tooluniverse -- tooluniverse`

`~/.claude.json` is app-managed. chezmoi owns only the keys it declares in
`home/modify_private_dot_claude.json`, and leaves everything Claude Code writes
alone — so MCP servers added with `claude mcp add` survive an apply.

Shared Claude Code and Codex skills are documented in
[Agent skills](agent-skills.md).

## Authentication and ephemeral environments

Configuration and authentication are separate. Plugins can be declared before
credentials exist; they simply fail to authenticate until supplied.

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

1. Bootstrap chezmoi — see [Installing and syncing](installing.md).
2. On Code Ocean, run `dotfiles-sync` so the capsule pass runs too.
3. Provide the applicable credentials as environment secrets.

Plugin configuration is independent of a scientific pipeline and may be omitted
from a reproducible capsule. Pyright LSP, basic PubMed access, and the bundled
skills require no token.
