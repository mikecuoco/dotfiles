# Development stages and reproducibility

## Exploration

- Prioritize correct, robust, logically organized code and fast interactive work; permit notebook state while questions are changing.
- Record enough context to preserve decisions and save expensive outputs rather than recomputing them casually.
- Consider memory, CPU concurrency, runtime, and input scale before expensive work; prefer bounded or chunked processing where practical.
- Address risks that could lose work, corrupt provenance, or fill root storage.
- Do not require end-to-end execution, `conda-lock`, or a finished `run`, and do not prompt for them.

## Stabilization

- Move expensive, unattended, or reused steps into scripts beside their notebooks.
- Make parameters explicit in scripts or nearby configuration.
- Separate immutable inputs, scratch intermediates, and final deliverables.
- Promote genuinely shared helpers into a package.
- Continue tracking CPU and memory costs as the workflow grows.
- Do not lock the environment or develop or invoke `run` unless the user explicitly requests that reproducibility work.

## Finalization

Perform this stage only when the user explicitly requests it. `conda-lock` remains separately opt-in if the request does not include locking.

- Make required work headless and deterministic.
- Remove reliance on hidden notebook execution order for required results.
- Make `run` small, executable, non-interactive, and explicit about failures.
- Let `run` orchestrate scripts; do not embed scientific implementation in it.
- Recreate final `/results` from declared inputs and environment.
- Make reruns safe, or state clearly when outputs are replaced.
- Test from a clean state with a Code Ocean Reproducible Run.

## Structural check

Use the bundled checker before making broad changes and after finalization:

```bash
python "<skill-dir>/scripts/check_capsule.py" --root / --stage auto
python "<skill-dir>/scripts/check_capsule.py" --root / --stage finalization --strict
```

For an exported repository, pass the repository root. `--format json` produces machine-readable findings. The checker does not execute scientific code and its findings require judgment; it deliberately treats missing final artifacts as informational during exploration.

## Finalization checklist

- Every required input is declared and indexed.
- Attached source data is never modified.
- Analysis-arm directories use stable `NN_name` prefixes.
- Expensive steps are scripted and parameterized.
- Random seeds and important analysis parameters are explicit.
- Required work does not depend on hidden notebook state.
- Shared code has clear imports and packaging.
- Environment constraints and lock agree, if locking was requested.
- Temp files, caches, builds, environments, downloads, and installations resolve under `/scratch`.
- `run` is executable, headless, minimal, and free of machine-specific paths.
- Intermediates go to `/scratch`; only final deliverables go to `/results`.
- A clean run recreates the expected deliverables.

In reviews, lead with current maturity and high-impact gaps. Distinguish confirmed defects from future-stage suggestions.
