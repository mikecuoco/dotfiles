# Clusters, budgets, and priorities for mike-cuoco

Verified 2026-10-04 for account `mike-cuoco` (`01KTYK3MQWK670SVQQDJW94T9Y`). These change: re-check with the commands at the end before relying on them for a large run, and update this file when they differ.

## Clusters

Probed 2026-10-04 with a 1-GPU, low-priority job per cluster on `mike-cuoco/torch-base-2.14.1-cu126-v1`. It ran `project-env` (boto3), `nvidia-smi`, a CUDA matmul, and an S3 list of `sea-ad-wg-802451596237-us-west-2/Multiregion` using the node role. Memory columns are what the job saw; "spec" means the job did not run and the value is NVIDIA's.

| Cluster | Usable by me | GPU | GPUs/node | GPU memory | CPUs/node | RAM/node | Nodes | S3 (node role) | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `ai1/octo-hub-aws-h200` | **Yes, ran** | H200 | 8 | 140 GiB | 192 | 2000 GiB | 4 | Read OK | Default. Sessions max 6 h. |
| `ai1/octo-hub-aws-l40s` | **Yes, ran** | L40S | 4 | 44 GiB | 48 | 373 GiB | 2 | Read OK | Usually has free slots. Sessions max 24 h. |
| `ai1/aipbd-aws-h200` | **Yes, ran** | H200 | 8 | 140 GiB | 192 | 2000 GiB | 5 | **Denied** (`AccessDenied` for `octo-aihub-ec2-node-role`) | Usually full: probe waited about 30 min. |
| `ai1/octo-hub-onprem-h200` | Allowed, not yet run | H200 | 8 | 141 GB spec | 224 | 3 TiB | 2 | Unknown | Full during probe: pending > 25 min. |
| `ai1/octo.hub-gcp-h200` | Allowed, not yet run | H200 | 8 | 141 GB spec | 224 | 2.8 TiB | 1 | Unknown | Full during probe: pending > 25 min. |
| `ai1/octo.ai-aws-p5en` | **No** | H200 | 8 | 141 GB spec | 192 | 2 TiB | 3 | — | "reserved for other users or budgets". |
| `ai1/octo.ai-aws-g6e` | **No** | L40S | 4 | 48 GB spec | 48 | 373 GiB | 4 | — | "reserved for other users or budgets". |
| `ai1/siti-aws-t4-dev` | **No** | T4 | 1 | 16 GB spec | 4 | 15 GiB | 1 | — | "reserved for other users or budgets". |
| `ai1/octo-hub-gcp-h100`, `ai1/dev-g6`, `ai1/aihub-dev-aws`, `ai1/octo-hub-aws-l40s-dev`, `ai1/aipbd-aws-h100-decomissioned` | — | | | | | | 0 | — | No nodes; jobs never schedule. |

- All probed nodes: x86_64, driver 580.105.08 (CUDA 13.0 capable). `project-env` with one small package took about 12 s.
- A 1-GPU slot on an 8-GPU H200 node is about 1/8 of the node (about 24 CPUs and 250 GiB RAM).
- Request memory that fits the node: on the T4 node (15 GiB), a 16 GiB request was canceled at once with "no nodes have enough resources".
- For S3-reading jobs, constrain to `ai1/octo-hub-aws-h200` and `ai1/octo-hub-aws-l40s`. For jobs without S3, add `ai1/aipbd-aws-h200`, `ai1/octo-hub-onprem-h200`, and `ai1/octo.hub-gcp-h200` to widen the pool.
- Cluster policies on usable clusters: `minRuntime` between 5 min and 8 h.

## Budgets

All three ran the probe on `ai1/octo-hub-aws-h200` at low priority on 2026-10-04.

| Budget | Status |
|---|---|
| `ai1/octo.aihub-lowpri` | Works; default for `ai1/seaad-drvi`. Use for testing and low-priority runs. |
| `ai1/octo.ai` | Works. Confirm with the AI Hub team before charging real runs to it. |
| `ai1/ai1-test` | Works. Intended for testing. |
| Project budgets (for example `ai1/aipbd-general`) | Not tested; need confirmation from the AI Hub team. |

## Priorities

- `low`: works on every usable cluster. Preemptible; auto-resumes from the start.
- `normal`: works (probe on `ai1/octo-hub-aws-h200` with `ai1/octo.aihub-lowpri`, 2026-10-04). Ask before using it for real runs.
- `high`, `urgent`: not allowed; `ai1/seaad-drvi` has `maxWorkloadPriority: normal`.

## Workspace and image

- Workspace: `ai1/seaad-drvi`.
- Base image: `mike-cuoco/torch-base-2.14.1-cu126-v1` (PyTorch 2.14.1, CUDA 12.6, built from [docker/](docker/Dockerfile)). Smoke-tested on an H200 on 2026-10-04.

## Re-check

```bash
beaker account whoami --format json                    # my user ID
beaker cluster list ai1                                # slots, session limits
beaker cluster get <cluster> --format json             # userRestrictions, budgetRestrictions
beaker cluster nodes <cluster> --format json           # GPU type/count, CPU, memory per node
beaker workspace get <workspace> --format json         # maxWorkloadPriority, default budget
```

I can use a cluster if its `userRestrictions` is empty or contains my user ID, and its `budgetRestrictions` is empty or contains the budget.
