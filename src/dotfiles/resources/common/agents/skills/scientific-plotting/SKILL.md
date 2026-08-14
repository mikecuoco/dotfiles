---
name: scientific-plotting
description: Create, revise, and review scientific plots and publication figures with accessible styling and deliverable-aware sizing. Use for seaborn or matplotlib figures, manuscript panels, posters, presentations, axis and uncertainty labeling, color choices, or figure export.
---

# Scientific Plotting

Prefer concise seaborn calls and use matplotlib only when additional control is needed. Apply the shared styles with:

```python
plt.style.use(["cuoco-base", "cuoco-presentation"])
```

Use `cuoco-manuscript` or `cuoco-poster` when the deliverable calls for it. Do not duplicate settings already supplied by the shared styles; follow venue requirements and change the shared styles only when the change should become a global default.

## Design the figure

- Choose the final medium and dimensions before polishing the plot.
- For manuscripts, use the final 89 mm or 183 mm width.
- Label manuscript panels with bold, upright, lowercase 8 pt letters.
- Never rely on color alone and avoid rainbow or red-green contrasts.
- Label axes with units and define error bars, intervals, and sample sizes.
- Keep annotations readable at the final export size.

## Validate

Inspect the rendered figure at its final dimensions. Check clipped labels, overlapping elements, legibility, accessibility, and whether the visual encoding supports the scientific claim. Report the output path, dimensions, and any assumptions about venue requirements.
