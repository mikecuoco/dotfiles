---
name: scientific-plotting
description: Create, revise, and review scientific figures for publication in matplotlib or seaborn. Use for manuscript panels, posters, conference presentations, figure sizing and export, axis and uncertainty labeling, or accessible color choices in Python plotting code. Not for web dashboards, interactive charts, or non-Python plotting.
---

# Scientific Plotting

Prefer concise seaborn calls and use matplotlib only when additional control is needed.

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
