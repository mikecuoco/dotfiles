# Safety

- Never expose or commit secrets; use environment variable injection.
- Never modify primary/source data in place.
- Keep derived and primary data clearly separate.

# Working style

- Lead with the answer. Keep prose concise.
- Write about 80% of the way to ASD-STE100 Simplified Technical English:
  - Use short sentences: at most 20 words for steps and 25 for descriptions.
  - Use the active voice, and the imperative for steps. Put one idea in each
    sentence.
  - Use common words, and one term for each concept. Do not use idioms or
    phrasal verbs.
  - Keep technical names, identifiers, and domain terms. Do not force the
    STE dictionary where it makes the text less precise.
- Use diagrams where possible to show structure, flow, or data movement. In
  plans, include ASCII diagrams.
- Investigate uncertainty; do not guess.
- Ask only when ambiguity materially affects the result.

# Engineering

- Read existing code and conventions; make the smallest readable change.
- Explore with robust, logical code and fast iteration; add reproducibility when
  analysis stabilizes or the user requests it.
- Do not refactor unrelated code, add dependencies without reason, or disable
  tests to make them pass.
- Test meaningful changes.
- Commit or push only when asked, unless the task or harness explicitly directs
  otherwise. Never force-push shared branches.
- Reference code as `file:line`. Show commands actually run.

# Compute resources

- Consider input scale, peak memory, concurrency, and recomputation; prefer
  bounded parallelism, streaming, or chunking when practical.

# Python

- Respect the project's environment manager and its declared Python floor.
- Do not mutate global/base environments. Do not create, refresh, require, or
  prompt for `conda-lock` unless asked.
- Use pathlib.Path, f-strings, and dataclasses. Use match/case only where the
  project already targets Python 3.11+.
- For channels, solvers, Jupyter kernels, and pinning, use the
  `conda-environments` skill.

# Project memory

- Project memories are individual Markdown files under `<repo>/.agents/memory/`,
  local to the checkout and not committed. At the start of repository work, scan
  filenames and read only memories relevant to the task.
- Treat memories as advisory and verify material claims against current project
  files.
- Before writing, updating, or removing a memory, use the `project-memory`
  skill.

# Project instructions

- At the start of repository work, find and follow the most specific applicable
  `CLAUDE.md` or `AGENTS.md`.
