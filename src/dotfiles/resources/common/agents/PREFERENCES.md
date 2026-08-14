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
- Pin dependencies when reproducibility is an explicit goal, not during early
  exploration without a concrete need.
- Use pathlib.Path, f-strings, dataclasses, match/case (Python 3.11+).

# Plotting

- Prefer concise seaborn calls; use matplotlib only for needed control.
- Apply `plt.style.use(["cuoco-base", "cuoco-presentation"])` by default; use `cuoco-manuscript` or `cuoco-poster` when the deliverable requires it.
- Do not duplicate shared style settings; follow venue requirements and update
  shared styles only for global defaults.
- For manuscripts, size figures at their final 89 mm or 183 mm width and label panels with bold, upright 8 pt lowercase letters.
- Never rely on color alone or use rainbow/red-green contrasts; label axes with
  units and define error bars and sample sizes.

# Jupyter notebooks

- Keep notebooks linear, fresh-kernel runnable, and composed of short,
  single-purpose cells. Put imports/configuration near the top.
- Use Markdown for intent, assumptions, and conclusions; prefer rich previews
  to verbose output. Extract reusable logic; seed randomness; address warnings.
- Never overwrite source data; keep derived outputs separate. Keep source
  notebooks unexecuted.
- Save executed copies as `<name>.out.ipynb`, regenerate after source changes,
  never edit directly, and keep them out of Git. Before finishing, restart and
  run all cells, saving results only to the `.out.ipynb` copy.

# Memory

- Store short, factual, durable, non-obvious conclusions—not transcripts,
  project-file facts, secrets, or sensitive data. Update or remove stale or
  conflicting memories.
- After every completed conversation, create a concise Markdown summary in both
  repository-local memory directories: `.claude/memory/` and
  `.codex/memories/`. Keep identical dated, descriptive files in sync.
- Include the request, decisions, changes, validation, durable lessons, and
  remaining work. Keep these files local and never commit them.

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
