"""Claude and Codex context budget reporter.

Measures the generated instruction chains for both agents and reports
per-profile effective totals. Uses a simple word-count approximation
(words × 4/3) — no external tokenizer required. The module name and
``run_claude_stats`` entry point remain as compatibility aliases.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Budget thresholds (estimated tokens, warnings only — not hard failures)
GLOBAL_BUDGET = 900
OVERLAY_BUDGET = 500


def estimate_tokens(text: str) -> int:
    """Return an estimated token count using a word-count approximation.

    Formula: words × 4 / 3 (rounds down).  This is a standard BPE
    approximation for English prose; good enough for budget checking.
    """
    return len(text.split()) * 4 // 3


def _measure(text: str) -> dict[str, int]:
    return {
        "lines": text.count("\n"),
        "words": len(text.split()),
        "tokens": estimate_tokens(text),
    }


def _fmt(label: str, stats: dict[str, int], budget: Optional[int] = None) -> str:
    lines = [label]
    lines.append(f"  lines:             {stats['lines']}")
    lines.append(f"  words:             {stats['words']}")
    tag = ""
    if budget is not None and stats["tokens"] > budget:
        tag = f"  [OVER BUDGET — limit {budget}]"
    lines.append(f"  estimated tokens:  {stats['tokens']}{tag}")
    return "\n".join(lines)


def _fmt_total(label: str, tokens: int, budget: Optional[int] = None) -> str:
    tag = ""
    if budget is not None and tokens > budget:
        tag = f"  [OVER BUDGET — limit {budget}]"
    return f"{label}\n  estimated tokens:  {tokens}{tag}"


def _instruction_sources(
    resources: Path,
    profile_name: str,
    destination: str,
) -> list[Path]:
    from .profiles import load_profiles, resolve_links

    profiles = load_profiles(resources)
    return [
        resources / link.src
        for link in resolve_links(profile_name, profiles)
        if link.dst == destination and link.mode in {"link", "append"}
    ]


def _compose(sources: list[Path]) -> str:
    return "\n\n".join(path.read_text() for path in sources)


def run_agent_stats(resources_dir: Optional[Path] = None) -> int:
    """Print agent context budgets. Returns 0 when every layer is in budget."""
    from . import RESOURCES_DIR
    from .profiles import load_profiles

    resources = resources_dir or RESOURCES_DIR
    profiles = load_profiles(resources)
    destinations = {
        "Claude": ".claude/CLAUDE.md",
        "Codex": ".codex/AGENTS.md",
    }

    print("Agent context budget")
    over_budget = False
    for agent_name, destination in destinations.items():
        common_sources = _instruction_sources(resources, "common", destination)
        missing = [path for path in common_sources if not path.exists()]
        if not common_sources or missing:
            detail = missing[0] if missing else destination
            print(f"Error: instruction source not found for {detail}", file=sys.stderr)
            return 1

        global_text = _compose(common_sources)
        global_stats = _measure(global_text)
        print()
        print(_fmt(f"{agent_name} global", global_stats, budget=GLOBAL_BUDGET))
        over_budget = over_budget or global_stats["tokens"] > GLOBAL_BUDGET

        for profile_name in sorted(profiles):
            if profile_name == "common":
                continue
            sources = _instruction_sources(resources, profile_name, destination)
            overlay_sources = sources[len(common_sources):]
            if not overlay_sources:
                continue
            overlay_text = _compose(overlay_sources)
            overlay_stats = _measure(overlay_text)
            effective_tokens = estimate_tokens(_compose(sources))

            print()
            print(_fmt(
                f"{agent_name} {profile_name} overlay",
                overlay_stats,
                budget=OVERLAY_BUDGET,
            ))
            print()
            print(_fmt_total(
                f"{agent_name} {profile_name} effective total",
                effective_tokens,
            ))
            over_budget = over_budget or overlay_stats["tokens"] > OVERLAY_BUDGET

    return 1 if over_budget else 0


def run_claude_stats(resources_dir: Optional[Path] = None) -> int:
    """Compatibility alias for the former Claude-only reporter."""
    return run_agent_stats(resources_dir=resources_dir)
