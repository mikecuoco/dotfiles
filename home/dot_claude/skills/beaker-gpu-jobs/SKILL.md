---
name: beaker-gpu-jobs
description: Submit, monitor, and debug batch GPU jobs on Beaker (Allen AI Hub, ai1 H200 clusters), typically from an HPC login or compute node. Use when moving a SLURM workload to Beaker; writing or reviewing a Beaker experiment spec; uploading code as a Beaker dataset; choosing a budget, cluster, image, or secrets; checking queue state, logs, or failures; or fetching results back to the HPC.
---

# Beaker GPU Jobs

Beaker runs containers on AWS GPU clusters. The HPC has no Docker and Beaker cannot see `/allen` or HPC scratch, so a job gets everything it needs from three places:

| What | Where it comes from | Changes when |
|---|---|---|
| Environment | A Beaker image built and uploaded from a Mac ([references/image-build.md](references/image-build.md)) | Dependencies change |
| Code | A Beaker dataset uploaded from the HPC and mounted read-only at `/code` | Every code change |
| Inputs | S3, read inside the job with the node's ambient AWS credentials | — |
| Outputs | `/results`, saved as a result dataset and fetched back | — |

Batch jobs are the default. For interactive debugging on a GPU see [references/sessions.md](references/sessions.md).

## Preflight (read-only)

```bash
beaker account whoami
beaker workspace get <workspace>          # shows DEFAULT BUDGET
beaker image get <user>/<image>           # short names do not resolve
beaker secret list --workspace <workspace> # names only; never read values
beaker cluster list ai1                   # SLOTS column shows free capacity per cluster
```

- Take workspace, image, budget, and secret names from the project, not from this skill. Look for `<repo>/beaker/README.md` or `.agents/memory/`; if absent, ask and then record them there.
- Budget: if the workspace has no default, pass one in the spec. `ai1/octo.aihub-lowpri` is for low-priority, preemptible testing. A project budget (for example `ai1/aipbd-general`) needs confirmation from the AI Hub team. Never run `beaker workspace set-budget` unless the user asks.
- Image and dataset references are owner-qualified: `<user>/<name>`.
- Free slots are not the same as usable slots. A cluster with `userRestrictions` or `budgetRestrictions` (`beaker cluster get <cluster> --format json`) only schedules for the listed user IDs or budgets; compare against `beaker account whoami --format json`. Restricted clusters show up in `job events` as nodes "reserved for other users or budgets".
- If the HPC has no `beaker` CLI, ask before installing it: `curl -fsSL https://beaker.org/install | sh` puts the binary in `$HOME/.local/bin` (override with `BEAKER_BIN_PATH`). Then authenticate with `beaker account login`. Never print or commit `~/.beaker/config.yml`; it holds the user token.

## Workflow

1. **Stage code.** Copy only what the job runs into a clean directory: scripts, small configs, a pinned package if needed. Exclude data, results, `.git`, `.env`, notebooks' outputs, and anything with credentials.
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

## Spec rules

- Run a smoke test first: 1 GPU, lowpri budget, a command that runs `nvidia-smi` and asserts `torch.cuda.is_available()`. Scale up only after it succeeds.
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
- Read S3 inside the job (boto3, `aws s3 cp`). Check the image actually has the client; if not, install it at the top of the command (`python -m pip install --quiet boto3`) or add it to the image. Use the `sea-ad-s3` skill to choose buckets and prefixes and to check paths read-only.
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
| `No module named boto3` | The image lacks the S3 client. Install it at the start of the command or add it to the image. |
| `exec format error` | Image built for ARM. Rebuild with `--platform linux/amd64`. |
| `/code/...: No such file` | Dataset not mounted or wrong name. Check `datasets[].source.beaker` and `beaker dataset ls <user>/<dataset>`. |
| `CUDA available: False` | Missing `resources.gpuCount`, or CPU-only PyTorch installed over the CUDA base image. |
| Empty results | Output written outside `result.path`. Write to `/results`. |

## References

- [references/experiment-spec.yaml](references/experiment-spec.yaml): annotated batch spec template.
- [references/image-build.md](references/image-build.md): building and uploading the environment image (Mac only).
- [references/sessions.md](references/sessions.md): interactive GPU sessions.
- AI Hub docs: [Beaker access](https://beaker-docs.alleninstitute.org/ai1/getting-started/beaker-access), [Budgets](https://beaker-docs.alleninstitute.org/ai1/getting-started/budgets), [Clusters](https://beaker-docs.alleninstitute.org/ai1/getting-started/clusters), [Interactive sessions](https://beaker-docs.alleninstitute.org/ai1/getting-started/interactive-sessions).
