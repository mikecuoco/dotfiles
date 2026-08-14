# Working style

- Lead with the answer. Keep prose concise.
- Investigate uncertainty; do not guess.
- Ask only when ambiguity materially affects the result.

# Engineering

- Read existing code and conventions; make the smallest readable change.
- Explore with robust, logical code and fast iteration; add reproducibility when
  analysis stabilizes or the user requests it.
- Do not refactor unrelated code, add dependencies without reason, or disable
  tests to make them pass.
- Test meaningful changes.
- Commit or push only when asked. Never force-push shared branches.
- Reference code as `file:line`. Show commands actually run.

# Compute resources

- Consider input scale, peak memory, concurrency, and recomputation; prefer
  bounded parallelism, streaming, or chunking when practical.

# Python

- Respect the project's environment manager; for new Python-only projects,
  prefer uv, or conda/mamba for native dependencies.
- Do not mutate global/base environments. Do not create, refresh, require, or
  prompt for `conda-lock` unless asked.
- When creating a Conda environment with a Jupyter kernel, register the kernel
  with Jupyter before finishing.
- Pin dependencies when reproducibility is an explicit goal, not during early
  exploration without a concrete need.
- Use pathlib.Path, f-strings, dataclasses, match/case (Python 3.11+).

# Project memory

- Store project-specific memories as individual Markdown files under
  `<repo>/.agents/memory/`. At the start of repository work, scan filenames and
  read only memories relevant to the task.
- Use one concise, descriptively named file per durable, non-obvious fact or
  decision. Update or remove stale and conflicting memories instead of adding
  duplicates.
- Treat memories as advisory and verify material claims against current project
  files. After changing memory, run `dotfiles memory check --repo <repo>` and
  mention any file created, updated, or removed in the final response.
- Do not store transcripts, task status, secrets, sensitive data, or facts that
  are already clear from project files. Keep required rules in checked-in
  project instructions or documentation.

# Project instructions

- At the start of repository work, find and follow the most specific applicable
  `CLAUDE.md` or `AGENTS.md`.
- Keep context focused; delegate substantial exploration in narrow tasks.
- Put stable repository conventions, workflows, and safety constraints in
  project instructions or documentation—not global memory. Propose updates for
  verified, non-obvious conventions only; exclude transient notes and secrets.

# Safety

- Never expose or commit secrets; use environment variable injection.
- Never modify primary/source data in place.
- Keep derived and primary data clearly separate.
