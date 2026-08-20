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

from . import chezmoi

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


#: Source template for each agent's instruction file, relative to the chezmoi
#: source directory. Rendering these is exactly what `chezmoi apply` does, so
#: the budget is measured against the bytes that actually get installed.
_TEMPLATES = {
    "Claude": "dot_claude/CLAUDE.md.tmpl",
    "Codex": "dot_codex/AGENTS.md.tmpl",
}


def _render(source: Path, agent: str, profile_name: str) -> str:
    """Render one agent's instruction file for *profile_name*."""
    return chezmoi.execute_template(source / _TEMPLATES[agent], profile=profile_name)


def run_agent_stats(source_dir: Optional[Path] = None) -> int:
    """Print agent context budgets. Returns 0 when every layer is in budget."""
    try:
        source = source_dir or chezmoi.source_dir()
    except chezmoi.ChezmoiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if source is None or not source.is_dir():
        print(
            "Error: could not locate the chezmoi source directory.\n"
            "Run: dotfiles install",
            file=sys.stderr,
        )
        return 1

    profile_names = sorted(chezmoi.data().get("layers", {}))
    if not profile_names:
        print("Error: no profiles found in the chezmoi source", file=sys.stderr)
        return 1

    print("Agent context budget")
    over_budget = False
    for agent_name in _TEMPLATES:
        try:
            global_text = _render(source, agent_name, "common")
        except chezmoi.ChezmoiError as exc:
            print(f"Error: could not render {agent_name} instructions: {exc}",
                  file=sys.stderr)
            return 1

        global_stats = _measure(global_text)
        print()
        print(_fmt(f"{agent_name} global", global_stats, budget=GLOBAL_BUDGET))
        over_budget = over_budget or global_stats["tokens"] > GLOBAL_BUDGET

        for profile_name in profile_names:
            if profile_name == "common":
                continue
            effective_text = _render(source, agent_name, profile_name)
            # The overlay is whatever the profile adds on top of the shared
            # base; comparing rendered output avoids re-deriving the layering.
            if effective_text == global_text:
                continue
            overlay_text = effective_text[len(global_text):]
            overlay_stats = _measure(overlay_text)

            print()
            print(_fmt(
                f"{agent_name} {profile_name} overlay",
                overlay_stats,
                budget=OVERLAY_BUDGET,
            ))
            print()
            print(_fmt_total(
                f"{agent_name} {profile_name} effective total",
                estimate_tokens(effective_text),
            ))
            over_budget = over_budget or overlay_stats["tokens"] > OVERLAY_BUDGET

    return 1 if over_budget else 0


def run_claude_stats(source_dir: Optional[Path] = None) -> int:
    """Compatibility alias for the former Claude-only reporter."""
    return run_agent_stats(source_dir=source_dir)
