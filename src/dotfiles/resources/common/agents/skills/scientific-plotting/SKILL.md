---
name: scientific-plotting
description: Create, revise, and review scientific figures for publication in matplotlib or seaborn, using the shared cuoco-* styles. Use for manuscript panels, posters, conference presentations, figure sizing and export, axis and uncertainty labeling, or accessible color choices in Python plotting code. Not for web dashboards, interactive charts, or non-Python plotting.
---

# Scientific Plotting

Prefer concise seaborn calls and use matplotlib only when additional control is needed. Apply the shared styles with:

```python
plt.style.use(["cuoco-base", "cuoco-presentation"])
```

Use `cuoco-manuscript` or `cuoco-poster` when the deliverable calls for it. Do not duplicate settings already supplied by the shared styles; follow venue requirements and change the shared styles only when the change should become a global default.

## Confirm the styles are installed

The `cuoco-*` styles ship with these dotfiles and are installed to `~/.matplotlib/stylelib/` on macOS and `~/.config/matplotlib/stylelib/` on Linux. They are not available on a machine that has not run `dotfiles install`. Check before relying on them:

```python
import matplotlib.style as mplstyle
missing = [s for s in ("cuoco-base",) if s not in mplstyle.available]
```

If a style is missing, say so and name the fix (`dotfiles install`, or `dotfiles install --profile linux` on a cluster). Do not silently substitute an unrelated style or hand-roll equivalent rcParams — the resulting figure will look close enough to pass review while being inconsistent with every other figure in the project.

## Design the figure

- Choose the final medium and dimensions before polishing the plot.
- For manuscripts, use the final 89 mm or 183 mm width.
- Label manuscript panels with bold, upright, lowercase 8 pt letters.
- Never rely on color alone and avoid rainbow or red-green contrasts.
- Label axes with units and define error bars, intervals, and sample sizes.
- Keep annotations readable at the final export size.

## Export

- Manuscripts and posters: vector PDF or SVG, so the figure stays sharp at any scale and text remains selectable.
- Raster only when required: PNG at 300 dpi minimum, 600 dpi for line art and text-heavy panels.
- Set the figure size explicitly rather than scaling after the fact; resizing a rendered figure changes the effective font size.
- Use `bbox_inches="tight"` to avoid clipped labels, and keep the paired source script or notebook cell so the figure can be regenerated.

## Validate

Inspect the rendered figure at its final dimensions. Check clipped labels, overlapping elements, legibility, accessibility, and whether the visual encoding supports the scientific claim. Report the output path, dimensions, format, and any assumptions about venue requirements.
