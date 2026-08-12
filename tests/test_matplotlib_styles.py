"""Structural checks for the shared Matplotlib style library."""
from pathlib import Path

import pytest

from dotfiles import RESOURCES_DIR


STYLE_DIR = RESOURCES_DIR / "common" / "matplotlib" / "stylelib"
STYLE_NAMES = {
    "cuoco-base.mplstyle",
    "cuoco-manuscript.mplstyle",
    "cuoco-presentation.mplstyle",
    "cuoco-poster.mplstyle",
}


def _style_keys(path: Path) -> list[str]:
    return [
        line.split(":", 1)[0].strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _style_values(path: Path) -> dict[str, str]:
    return {
        key.strip(): value.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
        for key, value in [line.split(":", 1)]
    }


def test_all_matplotlib_styles_exist():
    assert {path.name for path in STYLE_DIR.glob("*.mplstyle")} == STYLE_NAMES


def test_styles_do_not_repeat_rcparams():
    for path in STYLE_DIR.glob("*.mplstyle"):
        keys = _style_keys(path)
        assert len(keys) == len(set(keys)), f"Duplicate rcParam in {path.name}"


def test_base_style_owns_shared_visual_defaults():
    keys = set(_style_keys(STYLE_DIR / "cuoco-base.mplstyle"))
    assert {
        "font.family",
        "font.sans-serif",
        "axes.prop_cycle",
        "axes.spines.top",
        "axes.spines.right",
        "savefig.bbox",
        "pdf.fonttype",
    } <= keys


def test_context_styles_own_sizes_and_export_settings():
    required = {
        "figure.figsize",
        "font.size",
        "axes.titlesize",
        "axes.labelsize",
        "xtick.labelsize",
        "ytick.labelsize",
        "lines.linewidth",
        "lines.markersize",
        "savefig.format",
        "savefig.dpi",
    }
    for context in ("manuscript", "presentation", "poster"):
        keys = set(_style_keys(STYLE_DIR / f"cuoco-{context}.mplstyle"))
        assert required <= keys


def test_manuscript_style_matches_nature_defaults():
    values = _style_values(STYLE_DIR / "cuoco-manuscript.mplstyle")

    assert values["figure.figsize"].split(",", 1)[0].strip() == "3.5039"
    assert 5 <= float(values["font.size"]) <= 7
    assert 5 <= float(values["axes.labelsize"]) <= 7
    assert 5 <= float(values["xtick.labelsize"]) <= 7
    assert 0.25 <= float(values["axes.linewidth"]) <= 1
    assert 0.25 <= float(values["lines.linewidth"]) <= 1
    assert values["savefig.format"] == "pdf"
    assert values["savefig.dpi"] == "300"


def test_presentation_style_has_balanced_hierarchy():
    base = _style_values(STYLE_DIR / "cuoco-base.mplstyle")
    values = _style_values(STYLE_DIR / "cuoco-presentation.mplstyle")

    width, height = (float(part.strip()) for part in values["figure.figsize"].split(","))
    assert width / height == pytest.approx(16 / 9)
    assert float(values["figure.titlesize"]) > float(values["axes.titlesize"])
    assert float(values["axes.titlesize"]) > float(values["axes.labelsize"])
    assert float(values["axes.labelsize"]) > float(values["xtick.labelsize"])
    assert float(values["xtick.labelsize"]) >= float(values["legend.fontsize"])
    assert base["figure.constrained_layout.use"] == "True"
    assert base["savefig.bbox"] == "standard"


def test_styles_parse_when_matplotlib_is_available():
    matplotlib = pytest.importorskip("matplotlib")
    style = pytest.importorskip("matplotlib.style")
    base = STYLE_DIR / "cuoco-base.mplstyle"

    for context in ("manuscript", "presentation", "poster"):
        preset = STYLE_DIR / f"cuoco-{context}.mplstyle"
        with style.context([base, preset]):
            assert matplotlib.rcParams["font.family"] == ["sans-serif"]
            assert matplotlib.rcParams["axes.grid"] is False
