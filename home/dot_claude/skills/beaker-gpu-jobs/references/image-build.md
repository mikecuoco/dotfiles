# Building the environment image

Build and upload on a Mac with Docker Desktop. The HPC has no Docker. Rebuild only when dependencies change; code travels as a dataset.

## Dockerfile

Start from a CUDA PyTorch base and install the environment from an explicit lock file so the build is reproducible:

```dockerfile
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

COPY conda-explicit-linux-64 /tmp/environment.lock
RUN conda create --prefix /opt/conda/envs/workload --file /tmp/environment.lock \
    && conda clean --all --yes

ENV PATH="/opt/conda/envs/workload/bin:${PATH}"
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

WORKDIR /app
CMD ["/bin/bash"]
```

- No `ENTRYPOINT`: the batch command belongs in the spec, and sessions need a plain shell.
- Recreate the environment from YAML or a lock file; never copy an HPC Conda install into the image.
- Remove machine-specific `prefix:` lines. Make sure the environment does not install CPU-only PyTorch over the CUDA base.
- Generate the lock with the `conda-environments` skill (`conda-forge` above `bioconda`, `nodefaults` last).
- Never copy tokens, AWS credentials, SSH keys, or `.env` files. Use a `.dockerignore`:

  ```text
  .git
  .env
  .aws
  .ssh
  __pycache__
  *.pyc
  data/
  results/
  ```

## Build and upload

```bash
docker desktop start && docker info          # Server section must be populated
docker buildx build --platform linux/amd64 --load --tag <image>:<n> .
docker image inspect <image>:<n>
DOCKER_HOST="unix://$HOME/.docker/run/docker.sock" \
  beaker image create --workspace <workspace> --name <image>-v<n> <image>:<n>
beaker image get <user>/<image>-v<n>
```

- `--platform linux/amd64`: Apple Silicon builds ARM by default; Beaker nodes are x86. Keep the flag on the command, not the `FROM` line.
- `--load`: puts the buildx result in the local image store where `beaker image create` reads it.
- `DOCKER_HOST`: `beaker` looks for `/var/run/docker.sock`; Docker Desktop's socket is under `~/.docker/run/`.
- Bump the version suffix for every upload and record the new reference with the project's Beaker values.

## Errors

| Symptom | Fix |
|---|---|
| `Cannot connect to ... docker.sock` | Start Docker Desktop and set `DOCKER_HOST` as above. |
| Socket missing although Desktop "running" | `docker desktop restart`, then `docker info`. |
| ARM image rejected / `exec format error` | Rebuild with `--platform linux/amd64 --load`. |
| Session starts the training script | Remove `ENTRYPOINT`; keep `CMD ["/bin/bash"]`. |
