# Working style

- Lead with the answer. Keep prose concise.
- Investigate uncertainty; do not guess.
- Ask only when ambiguity materially affects the result.
- Be thorough when the task requires it, not by default.

# Engineering

- Read existing code and conventions before changing it.
- Make the smallest change that solves the problem.
- Prefer readable code over unnecessary abstraction.
- During exploration, prioritize robust, logical code and fast iteration over reproducibility infrastructure.
- Add reproducibility only when analysis stabilizes or the user requests it; do not prematurely finalize exploratory work.
- Do not refactor unrelated code or add dependencies without reason.
- Test meaningful changes. Never disable tests to make them pass.
- Commit or push only when asked. Never force-push shared branches.
- Reference code as `file:line`. Show commands actually run.

# Compute resources

- Always consider CPU and memory, including input scale, peak memory, concurrency, and recomputation.
- Prefer bounded parallelism and streaming or chunking when practical; surface material constraints.

# Python

- Respect the project's existing environment manager.
- For new Python-only projects, prefer uv.
- Use conda/mamba when native dependencies make it useful.
- Don't mutate global/base environments; create named envs.
- Do not create, refresh, require, or prompt for `conda-lock` unless the user explicitly asks for it.
- Pin dependencies when reproducibility becomes an explicit goal; do not let early pinning slow exploratory iteration without a concrete need.
- Use pathlib.Path, f-strings, dataclasses, match/case (Python 3.11+).

# Plotting

- Prefer concise seaborn calls over direct matplotlib code.
- Use matplotlib only when seaborn cannot provide the required control.
- Apply `plt.style.use(["cuoco-base", "cuoco-presentation"])` by default; use `cuoco-manuscript` or `cuoco-poster` when the deliverable requires it.
- Do not duplicate shared style settings in notebooks or project helpers; override only plot-specific needs.
- Follow venue requirements when provided; update the shared style only when a default should change globally.
- For manuscripts, size figures at their final 89 mm or 183 mm width and label panels with bold, upright 8 pt lowercase letters.
- Never rely on color alone or use rainbow or red-green contrasts; label axes with units and define error bars and exact sample sizes.

# Jupyter notebooks

- Keep notebooks linear and runnable top-to-bottom from a fresh kernel.
- Use short, single-purpose cells; avoid hidden state and duplicated logic.
- Put imports and configuration near the top.
- Use Markdown to explain intent, assumptions, and conclusions.
- Prefer rich display and small previews over verbose printed output.
- Extract reusable or complex logic into modules or functions.
- Set random seeds when results depend on randomness.
- Never overwrite source data; keep derived outputs separate.
- Address warnings rather than suppressing them globally.
- Keep source notebooks unexecuted.
- Save executed copies beside their sources as `<name>.out.ipynb`.
- Regenerate the `.out.ipynb` copy whenever its source changes; never edit it directly.
- Treat `*.out.ipynb` as derived output and keep it out of Git.
- Restart the kernel and run all cells before finishing, saving the executed result only to the `.out.ipynb` copy.

# Context & agents

- Keep the main context small; retrieve only what is relevant.
- Use subagents to isolate substantial exploration.
- Give subagents narrow tasks and request concise findings.

# Memory

- Store durable, non-obvious facts useful to future sessions.
- Store conclusions, not task transcripts.
- Keep memories short and factual.
- Update or remove stale or conflicting memories.
- Do not store facts already obvious from project files.

# Safety

- Never expose or commit secrets; use environment variable injection.
- Never modify primary/source data in place.
- Keep derived and primary data clearly separate.
