# Interactive GPU sessions

Use a session to debug inside the image on a GPU. Use batch experiments for real runs. Sessions hold a GPU until they are stopped, and some clusters cap session length (`beaker cluster get` shows `MAX SESSION TIMEOUT`).

```bash
beaker session create \
  --remote --bare \
  --workspace <workspace> \
  --budget <budget> \
  --cluster ai1/aipbd-aws-h200 --cluster ai1/octo-hub-aws-h200 \
  --gpus 1 \
  --key ~/.ssh/id_ed25519 \
  --image beaker://<user>/<image>
```

- `--bare` gives a shell without running an entrypoint.
- Add `--min-runtime 2h` to protect a low-priority session from preemption for that long.
- Use `--detach` instead of `--remote` to start it in the background.
- No Docker is needed; the image is already in Beaker.

Inside the session:

```bash
nvidia-smi
python -c 'import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())'
```

Reconnect, add a shell, and stop:

```bash
beaker session attach --remote <session-id>
beaker session exec --remote <session-id> -- bash
beaker session stop <session-id>
```

Exit or stop every session when finished; an idle session still consumes budget.
