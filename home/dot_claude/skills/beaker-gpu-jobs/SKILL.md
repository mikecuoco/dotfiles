---
name: beaker-gpu-jobs
description: Submit, monitor, and debug batch GPU jobs on Beaker (Allen AI Hub, ai1 H200 clusters), typically from an HPC login or compute node. Use when moving a SLURM workload to Beaker; writing or reviewing a Beaker experiment spec; uploading code as a Beaker dataset; choosing a budget, cluster, image, or secrets; checking queue state, logs, or failures; or fetching results back to the HPC.
---

# Beaker GPU Jobs

Beaker runs containers on AWS GPU clusters. The HPC has no Docker and Beaker cannot see `/allen` or HPC scratch, so a job gets everything it needs from three places:

| What | Where it comes from | Changes when |
|---|---|---|
| CUDA + PyTorch | One shared base image for all projects ([references/image-build.md](references/image-build.md)) | PyTorch or CUDA bump |
| Project env | `env/environment.yml` in the code dataset, built by `project-env` at job start | Every code dataset |
| Code | A Beaker dataset uploaded from the HPC and mounted read-only at `/code` | Every code change |
| Inputs | S3, read inside the job with the node's ambient AWS credentials | — |
| Outputs | `/results`, saved as a result dataset and fetched back | — |

Which clusters, budgets, and priorities work for this account, and each cluster's GPUs and memory: [references/clusters.md](references/clusters.md). Batch jobs are the default. For interactive debugging on a GPU see [references/sessions.md](references/sessions.md).

## Preflight (read-only)

```bash
beaker account whoami
beaker workspace get <workspace>          # shows DEFAULT BUDGET
beaker image get <user>/<image>           # short names do not resolve
beaker secret list --workspace <workspace> # names only; never read values
beaker cluster list ai1                   # SLOTS column shows free capacity per cluster
```

- Start from [references/clusters.md](references/clusters.md) for this account's verified workspace, image, budgets, clusters, and priorities. Take project-specific names (code datasets, secrets, a project workspace or budget) from the project, not from this skill. Look for `<repo>/beaker/README.md` or `.agents/memory/`; if absent, ask and then record them there.
- Budget: if the workspace has no default, pass one in the spec. `ai1/octo.aihub-lowpri` is for low-priority, preemptible testing. A project budget (for example `ai1/aipbd-general`) needs confirmation from the AI Hub team. Never run `beaker workspace set-budget` unless the user asks.
- Image and dataset references are owner-qualified: `<user>/<name>`.
- Free slots are not the same as usable slots. A cluster with `userRestrictions` or `budgetRestrictions` (`beaker cluster get <cluster> --format json`) only schedules for the listed user IDs or budgets; compare against `beaker account whoami --format json`. Restricted clusters show up in `job events` as nodes "reserved for other users or budgets".
- If the HPC has no `beaker` CLI, ask before installing it: `curl -fsSL https://beaker.org/install | sh` puts the binary in `$HOME/.local/bin` (override with `BEAKER_BIN_PATH`). Then authenticate with `beaker account login`. Never print or commit `~/.beaker/config.yml`; it holds the user token.

## Workflow

1. **Stage code.** Copy only what the job runs into a clean directory: scripts, small configs, a pinned package if needed, and the project env as `env/environment.yml` (see [Project env](#project-env)). Exclude data, results, `.git`, `.env`, notebooks' outputs, and anything with credentials.
2. **Upload code.** Use a timestamped, immutable name so every experiment points at the exact code it ran:
   ```bash
   STAMP=$(date +%Y%m%d-%H%M)
   beaker dataset create <staging-dir> --workspace <workspace> \
     --name <project>-code-$STAMP --desc "<git commit or short note>"
   ```
3. **Write the spec.** Copy [references/experiment-spec.yaml](references/experiment-spec.yaml) to `<repo>/beaker/<job>.yaml` and fill in the placeholders. Keep specs in version control; they are the job's provenance.
4. **Review, then submit.** Show the user the spec and the budget, GPU count, and priority before submitting.
   ```bash
   beaker experiment create --workspace <workspace> --name <job>-$STAMP beaker/<job>.yaml
   ```
   Record the experiment ID it prints.
5. **Monitor.**
   ```bash
   beaker experiment get <exp>                       # status per task
   beaker job events <job-id>                        # why it is not scheduled
   beaker job logs --follow <job-id>                 # stream while running
   beaker experiment logs <exp> --tail 50            # after it finishes
   beaker experiment await-all <exp> --timeout 2h    # block until terminal
   ```
   `beaker experiment get <exp> --format json` gives job IDs and `status` fields (`scheduled`, `started`, `exitCode`, `finalized`, `message`).
6. **Fetch results** to project or scratch storage on the HPC, never next to primary data:
   ```bash
   beaker experiment results <exp> --output <results-dir>/<job>-$STAMP
   ```
   The result dataset has one folder per task. Write a small `run.meta.json` from inside the job (code dataset name, image, git commit, parameters) so the fetched folder is self-describing.

## Project env

The image has CUDA and PyTorch but no project packages. Each job runs `project-env` first, so one image serves every project:

```bash
project-env    # /code/env/environment.yml -> /opt/env, first on PATH
```

It creates `/opt/env` with the image's Python version, adds a `.pth` entry so the env imports the image's pip-installed torch, installs the env file, and fails if the env ends up with its own torch ([references/docker/project-env](references/docker/project-env)).

- Do not list `python`, `pytorch`, or CUDA packages; the image provides them. Read the versions from the image (`/usr/bin/python3 --version`, `$PYTORCH_VERSION`) when a dependency needs them.
- Conda does not see the image's torch. A conda package that depends on `pytorch` (for example `scvi-tools`) pulls a second, conda-built torch and `project-env` fails. Put torch-dependent packages under `pip:` in the env file; pip sees the image's torch and reuses it.
- Everything else, including `boto3` or `awscli` for S3, goes in the env file. Channels follow the `conda-environments` skill; the image already defaults to conda-forge then bioconda with strict priority.
- The install downloads the project's packages on every task; a small env (pandas plus one pip package) took about 20 s on an H200 node. For many short tasks, batch work into fewer tasks or build a project image on the base ([references/image-build.md](references/image-build.md#project-specific-image-fallback)).

## Spec rules

- Run a smoke test first: 1 GPU, lowpri budget, `project-env`, `nvidia-smi`, and the CUDA assertion from the template. Scale up only after it succeeds.
- Put the real command in the spec (`command: [bash, -lc]`, `set -euo pipefail`). Images must not have an `ENTRYPOINT`.
- `constraints.cluster` is task-level, not under `context`. Omit it only for CPU-only jobs that can run anywhere.
- `context.priority: low` jobs can be preempted; Beaker stores `autoResume: true` and reruns the task from the start. Make long jobs resumable: checkpoint to `/results` or S3 and skip completed work on restart. `context.minRuntime` buys protection from preemption for that long.
- Request `cpuCount` and `memory` anyway. H200 nodes are allocated in GPU slots, so a 1-GPU job got about 24 CPUs and 250 GiB regardless; the request matters for CPU-only jobs and for packing.
- One task per independent unit of work; use multiple tasks (or experiments) rather than a shell loop over samples.

## Data and secrets

- Start with ambient credentials: AI Hub AWS nodes carry an IAM role, so a job with no AWS env vars can read buckets that role is granted.
- That access differs by cluster. On 2026-10-03, listing `sea-ad-wg-*` worked on `ai1/octo-hub-aws-h200` and `ai1/octo-hub-aws-l40s` and was denied on `ai1/aipbd-aws-h200`. Pin S3-reading jobs to clusters that passed a CPU-only S3 smoke test, and record the verified clusters with the project's Beaker values.
- Do not pass AWS key secrets by default. Environment credentials override the node role, so a stale session token turns a working job into `ExpiredToken`.
- If a bucket needs explicit keys, inject them only via `envVars[].secret` references. Never inline values, bake them into an image, or upload them in the code dataset.
- Read S3 inside the job (boto3, `aws s3 cp`). Add the client to `env/environment.yml`; the base image does not have it. Use the `sea-ad-s3` skill to choose buckets and prefixes and to check paths read-only.
- Writing to S3 from a job is an upload: ask the user before adding it.
- `beaker dataset create` with data is fine for small inputs; it is slow for large ones.
- AI Hub H200 nodes mount a shared Lustre filesystem at `/workspacedata` with per-project directories. It is not provisioned per Beaker workspace automatically; ask the AI Hub team before relying on it.
- Treat fetched results as derived data.

## Guardrails

- Ask before submitting anything that is not low priority, uses more than 1 GPU, or is expected to run for hours.
- Never stop, cancel, or change priority on experiments you did not create in this session: `beaker experiment stop <exp>` only for your own.
- On the HPC, do not run large `dataset create` or `experiment results` transfers on a login node; use a compute allocation.
- Check `beaker cluster get` before promising a start time. With `SLOTS` at `0 free`, a 1-GPU low-priority job has waited about 12 minutes; larger requests can wait much longer.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Error: no budget specified` | Workspace has no default. Add `budget:` to the spec. |
| Image short name not found | Use `<user>/<image>`; sessions need `beaker://<user>/<image>`. |
| `FailedScheduling ... not enough slots` in `job events` | Clusters are full. Wait, widen `constraints.cluster`, or ask about a different budget. Not a spec error. |
| `No such image: gcr.io/...: image not found` at start | Transient node image-cache failure; Beaker retries. Resubmit if it does not. |
| `AccessDenied ... assumed-role/...-node-role` from S3 | That cluster's node role cannot read the bucket. Constrain the task to a cluster that passed the S3 smoke test, or ask the AI Hub team to grant the role. |
| `ExpiredToken` from S3 | A secret holds expired session credentials and overrides the node role. Remove the `AWS_*` secret env vars, or refresh the secret. |
| `No module named boto3` | Add `boto3` to `env/environment.yml`. |
| `env shadows the image torch` from `project-env` | A conda package pulled its own `pytorch`. Move it under `pip:` in the env file. |
| `project-env` cannot solve, mentioning `python` | The env file pins a Python the image does not have. Remove the pin. |
| Job spends minutes before the entry point | `project-env` is downloading. Trim the env, batch tasks, or use a project-specific image. |
| `exec format error` | Image built for ARM. Rebuild with `--platform linux/amd64`. |
| `/code/...: No such file` | Dataset not mounted or wrong name. Check `datasets[].source.beaker` and `beaker dataset ls <user>/<dataset>`. |
| `CUDA available: False` | Missing `resources.gpuCount`, or the image's CUDA does not match the node driver. |
| Empty results | Output written outside `result.path`. Write to `/results`. |

## References

- [references/experiment-spec.yaml](references/experiment-spec.yaml): annotated batch spec template.
- [references/image-build.md](references/image-build.md): building and uploading the shared base image (Mac only).
- [references/docker/](references/docker/Dockerfile): the base image source (`Dockerfile`, `condarc`, `project-env`).
- [references/sessions.md](references/sessions.md): interactive GPU sessions.
- [references/clusters.md](references/clusters.md): usable clusters with GPU type, count, and memory; budgets; priorities.
- AI Hub docs: [Beaker access](https://beaker-docs.alleninstitute.org/ai1/getting-started/beaker-access), [Budgets](https://beaker-docs.alleninstitute.org/ai1/getting-started/budgets), [Clusters](https://beaker-docs.alleninstitute.org/ai1/getting-started/clusters), [Interactive sessions](https://beaker-docs.alleninstitute.org/ai1/getting-started/interactive-sessions).
